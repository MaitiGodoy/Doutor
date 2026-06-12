"""
WardenAgent – governance enforcement agent.
Extends AutonomousAgentLoop and adds veto, audit_rule, enforce_policy.
"""
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.autonomy.core.agent_loop import AutonomousAgentLoop, AgentContext
from kernel.guards import SecurityGuard
from kernel.provider_router import get_provider_router
from kernel.sandbox import NemoClawSandbox


CONFIG_PATH = Path(__file__).resolve().parents[2] / "governance_config.json"
LOG_PATH = Path(__file__).resolve().parents[4] / "logs" / "warden_audit.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class WardenAgent(AutonomousAgentLoop):
    """Governance warden that can veto, audit, and enforce policies."""

    def __init__(self, goal: str = "governance enforcement", max_iterations: int = 5):
        super().__init__(goal=goal, max_iterations=max_iterations)
        # Override router to use async route via provider_router
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.sandbox = NemoClawSandbox()
        self.policies = self._load_policies()

    # ---------- Policy loading ----------
    def _load_policies(self) -> Dict[str, Any]:
        if CONFIG_PATH.exists():
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    # ---------- Public governance API ----------
    def veto(self, prompt: str) -> bool:
        """
        Return True if the prompt violates any policy (i.e., should be blocked).
        Uses SecurityGuard validation and policy keyword matching.
        """
        # Guard validation
        result = self.guard.validate_input(prompt, context={"chain_id": self.ctx.run_id})
        if result.status == "blocked":
            self._log_veto(prompt, result, reason="guard")
            return True

        # Policy keyword matching
        for policy_id, policy in self.policies.items():
            keywords = policy.get("block_keywords", [])
            if any(kw.lower() in prompt.lower() for kw in keywords):
                self._log_veto(prompt, {"policy_id": policy_id}, reason="policy_keyword")
                return True
        return False

    def audit_rule(self, policy_id: str) -> Dict[str, Any]:
        """
        Return a detailed audit report for a given policy_id.
        Uses LLM via provider_router to summarise policy intent.
        """
        policy = self.policies.get(policy_id, {})
        prompt = (
            f"Policy ID: {policy_id}\n"
            f"Policy definition: {json.dumps(policy, ensure_ascii=False)}\n"
            "Provide a concise audit summary with fields: purpose, risk_level, recommendations."
        )
        # provider_router.route is async; run synchronously via event loop
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        summary = loop.run_until_complete(self.router.route(prompt, context={"chain_id": self.ctx.run_id}, priority="high"))
        try:
            audit = json.loads(summary)
        except json.JSONDecodeError:
            audit = {"purpose": "unknown", "risk_level": "unknown", "recommendations": []}
        audit["policy_id"] = policy_id
        audit["timestamp"] = time.time()
        return audit

    def enforce_policy(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enforce all policies on a given execution context (e.g., tool call).
        Returns dict with allowed (bool) and details.
        """
        # Validate output if present
        output_text = context.get("output", "")
        if output_text:
            result = self.guard.validate_output(output_text, context={"chain_id": self.ctx.run_id})
            if result.status == "blocked":
                self._log_veto(output_text, result, reason="guard_output")
                return {"allowed": False, "reason": "output_blocked", "details": result.model_dump()}

        # Policy rule evaluation via sandbox for complex logic
        for policy_id, policy in self.policies.items():
            rule_code = policy.get("enforcement_rule")
            if rule_code:
                # rule_code should be a python expression returning bool, with `ctx` variable
                try:
                    exec_result = self.sandbox.run("python", code=rule_code, timeout=5)
                    if not exec_result.get("success"):
                        continue
                    # The sandbox returns result dict with output
                    allowed = exec_result.get("result", {}).get("output", "").strip() == "True"
                    if not allowed:
                        self._log_veto(str(context), {"policy_id": policy_id}, reason="enforcement_rule")
                        return {"allowed": False, "reason": f"policy_{policy_id}_failed", "details": exec_result}
                except Exception as e:
                    # On error, treat as violation
                    self._log_veto(str(context), {"policy_id": policy_id, "error": str(e)}, reason="enforcement_error")
                    return {"allowed": False, "reason": "enforcement_error", "details": str(e)}

        return {"allowed": True, "reason": "all_checks_passed"}

    # ---------- Logging ----------
    def _log_veto(self, content: str, detail: Dict[str, Any], reason: str) -> None:
        entry = {
            "timestamp": time.time(),
            "run_id": self.ctx.run_id,
            "reason": reason,
            "content_snippet": content[:200],
            "detail": detail,
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Override run to also log each iteration vetoes if needed
    def run(self) -> AgentContext:
        # Use parent run but could add governance-specific steps
        return super().run()
