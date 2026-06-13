"""
WardenAgent – Governance enforcement agent.
Extends AutonomousAgentLoop. Implements veto, audit_rule, enforce_policy.
Zero stubs. 100% funcional.
"""
import json
import time
import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from kernel.autonomy.core.agent_loop import AutonomousAgentLoop, AgentContext
from kernel.guards import SecurityGuard
from kernel.provider_router import get_provider_router
from kernel.sandbox import NemoClawSandbox


CONFIG_PATH = Path(__file__).resolve().parent / "governance_config.json"
LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "warden_audit.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class WardenAgent(AutonomousAgentLoop):
    """Governance warden that can veto, audit, and enforce policies."""

    def __init__(
        self,
        goal: str = "governance enforcement",
        max_iterations: int = 5,
        dry_run: bool = True,
    ):
        super().__init__(goal=goal, max_iterations=max_iterations, dry_run=dry_run)
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.sandbox = NemoClawSandbox()
        self.policies = self._load_policies()
        self.risk_threshold = self.policies.get("global", {}).get("risk_threshold", 0.7)

    # ---------- Policy loading ----------
    def _load_policies(self) -> Dict[str, Any]:
        if CONFIG_PATH.exists():
            with CONFIG_PATH.open("r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def reload_policies(self) -> Dict[str, Any]:
        """Reload policies from config file."""
        self.policies = self._load_policies()
        self.risk_threshold = self.policies.get("global", {}).get("risk_threshold", 0.7)
        return self.policies

    # ---------- Public governance API ----------
    async def veto(self, prompt: str) -> Dict[str, Any]:
        """
        Evaluate if a prompt should be blocked.
        Returns dict with blocked (bool), risk_score, flags, reason, and details.
        """
        # Guard validation
        result = self.guard.validate_input(prompt, context={"chain_id": self.ctx.chain_id})
        guard_blocked = result.status == "blocked"
        risk_score = result.risk_score
        flags = result.flags

        # Policy keyword matching
        policy_violations = []
        for policy_id, policy in self.policies.get("policies", {}).items():
            keywords = policy.get("block_keywords", [])
            hits = [kw for kw in keywords if kw.lower() in prompt.lower()]
            if hits:
                policy_violations.append({"policy_id": policy_id, "matched_keywords": hits})

        policy_blocked = len(policy_violations) > 0
        blocked = guard_blocked or policy_blocked or risk_score >= self.risk_threshold

        reason = []
        if guard_blocked:
            reason.append("guard")
        if policy_blocked:
            reason.append("policy_keyword")
        if risk_score >= self.risk_threshold:
            reason.append("risk_threshold")

        detail = {
            "blocked": blocked,
            "risk_score": risk_score,
            "flags": flags,
            "reason": reason,
            "guard_result": result.model_dump() if hasattr(result, "model_dump") else result.__dict__,
            "policy_violations": policy_violations,
            "threshold": self.risk_threshold,
        }

        if blocked:
            self._log_veto(prompt, detail, reason=",".join(reason))

        return detail

    def veto_sync(self, prompt: str) -> Dict[str, Any]:
        """Synchronous wrapper for veto."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.veto(prompt))

    async def audit_rule(self, policy_id: str) -> Dict[str, Any]:
        """
        Return a detailed audit report for a given policy_id.
        Uses LLM via provider_router to summarise policy intent.
        """
        policy = self.policies.get("policies", {}).get(policy_id, {})
        if not policy:
            return {
                "policy_id": policy_id,
                "error": "policy_not_found",
                "timestamp": time.time(),
            }

        prompt = (
            f"Policy ID: {policy_id}\n"
            f"Policy definition: {json.dumps(policy, ensure_ascii=False)}\n"
            "Provide a concise audit summary as JSON with fields: "
            "purpose (string), risk_level (low|medium|high), recommendations (array of strings)."
        )

        summary = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            audit = json.loads(summary)
        except json.JSONDecodeError:
            audit = {"purpose": "unknown", "risk_level": "unknown", "recommendations": []}

        audit["policy_id"] = policy_id
        audit["timestamp"] = time.time()
        audit["policy_definition"] = policy
        return audit

    def audit_rule_sync(self, policy_id: str) -> Dict[str, Any]:
        """Synchronous wrapper for audit_rule."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.audit_rule(policy_id))

    async def enforce_policy(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enforce all policies on a given execution context (e.g., tool call).
        Returns dict with allowed (bool) and details.
        """
        # Validate output if present
        output_text = context.get("output", "")
        if output_text:
            result = self.guard.validate_output(output_text, context={"chain_id": self.ctx.chain_id})
            if result.status == "blocked":
                self._log_veto(output_text, {"guard_result": result.model_dump() if hasattr(result, "model_dump") else result.__dict__}, reason="guard_output")
                return {"allowed": False, "reason": "output_blocked", "details": result.model_dump() if hasattr(result, "model_dump") else result.__dict__}

        # Policy rule evaluation via sandbox for complex logic
        for policy_id, policy in self.policies.get("policies", {}).items():
            rule_code = policy.get("enforcement_rule")
            if rule_code:
                # rule_code should be a python expression returning bool, with `ctx` variable
                try:
                    exec_globals = {"ctx": context}
                    exec_result = self.sandbox.run("python", code=rule_code, globals_dict=exec_globals, timeout=5)
                    if not exec_result.get("success"):
                        continue
                    allowed = exec_result.get("result", {}).get("output", "").strip() == "True"
                    if not allowed:
                        self._log_veto(str(context), {"policy_id": policy_id}, reason="enforcement_rule")
                        return {"allowed": False, "reason": f"policy_{policy_id}_failed", "details": exec_result}
                except Exception as e:
                    self._log_veto(str(context), {"policy_id": policy_id, "error": str(e)}, reason="enforcement_error")
                    return {"allowed": False, "reason": "enforcement_error", "details": str(e)}

        return {"allowed": True, "reason": "all_checks_passed"}

    def enforce_policy_sync(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous wrapper for enforce_policy."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(self.enforce_policy(context))

    # ---------- Logging ----------
    def _log_veto(self, content: str, detail: Dict[str, Any], reason: str) -> None:
        entry = {
            "timestamp": time.time(),
            "run_id": self.ctx.run_id,
            "chain_id": self.ctx.chain_id,
            "reason": reason,
            "content_snippet": content[:200],
            "detail": detail,
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ---------- Utility ----------
    def list_policies(self) -> Dict[str, Any]:
        """Return all loaded policies."""
        return self.policies.get("policies", {})

    def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific policy by ID."""
        return self.policies.get("policies", {}).get(policy_id)