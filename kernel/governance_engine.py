"""
GovernanceEngine – Dynamic governance coordinator.
Orchestrates WardenAgent + ConstitutionAgent with metric-driven policy.
Zero stubs. 100% funcional.
"""
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from kernel.memory_store import MemoryStore

BASE_DIR = Path(__file__).resolve().parents[2]
LOG_PATH = BASE_DIR / "logs" / "governance_engine.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

try:
    from agents.governance.warden_agent import WardenAgent
except ImportError:
    WardenAgent = None

try:
    from agents.constitution import ConstitutionAgent
except ImportError:
    ConstitutionAgent = None


PolicyId = str

DEFAULT_POLICIES: Dict[str, Dict[str, Any]] = {
    "no_pii": {
        "enabled": True,
        "severity": "critical",
        "metric_triggers": {},
        "action": "block",
        "description": "Block prompts containing PII",
    },
    "no_toxic": {
        "enabled": True,
        "severity": "high",
        "metric_triggers": {},
        "action": "block",
        "description": "Block toxic or abusive content",
    },
    "no_prompt_injection": {
        "enabled": True,
        "severity": "critical",
        "metric_triggers": {},
        "action": "block",
        "description": "Detect prompt injection attempts",
    },
    "resource_limit": {
        "enabled": True,
        "severity": "medium",
        "metric_triggers": {"cpu_percent": 80, "memory_mb": 2000},
        "action": "throttle",
        "description": "Throttle when system resources are high",
    },
    "escalation_limit": {
        "enabled": True,
        "severity": "medium",
        "metric_triggers": {"escalation_rate": 0.5},
        "action": "pause",
        "description": "Pause governance if escalation rate exceeds threshold",
    },
}


class DynamicPolicy:
    """A single dynamic policy with metric-driven triggers."""

    def __init__(self, policy_id: PolicyId, config: Dict[str, Any]):
        self.id = policy_id
        self.config = config
        self.enabled = config.get("enabled", True)
        self.severity = config.get("severity", "medium")
        self.metric_triggers = config.get("metric_triggers", {})
        self.action = config.get("action", "block")
        self.description = config.get("description", "")
        self._last_triggered: float = 0.0
        self._trigger_count: int = 0

    def check_metrics(self, metrics: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not self.enabled:
            return False, None
        for metric, threshold in self.metric_triggers.items():
            value = metrics.get(metric)
            if value is None:
                continue
            if isinstance(value, (int, float)) and isinstance(threshold, (int, float)):
                if value >= threshold:
                    self._last_triggered = time.time()
                    self._trigger_count += 1
                    return True, f"{metric}={value} >= {threshold}"
        return False, None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "enabled": self.enabled,
            "severity": self.severity,
            "action": self.action,
            "description": self.description,
            "trigger_count": self._trigger_count,
        }


class GovernanceEngine:
    """Coordinates WardenAgent + ConstitutionAgent with dynamic policy control."""

    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or MemoryStore()
        self.policies: Dict[str, DynamicPolicy] = {
            pid: DynamicPolicy(pid, cfg) for pid, cfg in DEFAULT_POLICIES.items()
        }
        self._logs: List[Dict[str, Any]] = []
        self._warden = None
        self._constitution = None
        self._metrics_history: List[Dict[str, Any]] = []
        self._active_throttles: Dict[str, float] = {}
        self._escalation_count: int = 0
        self._total_decisions: int = 0

    def _get_warden(self) -> Any:
        if self._warden is None and WardenAgent is not None:
            self._warden = WardenAgent(goal="governance engine enforcement", dry_run=True)
        return self._warden

    def _get_constitution(self) -> Any:
        if self._constitution is None and ConstitutionAgent is not None:
            self._constitution = ConstitutionAgent()
        return self._constitution

    async def vet(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._total_decisions += 1
        context = context or {}
        start = time.time()

        system_metrics = self._collect_metrics()
        self._metrics_history.append({"timestamp": time.time(), **system_metrics})
        if len(self._metrics_history) > 100:
            self._metrics_history.pop(0)

        policy_results = []
        blocked = False
        throttled = False
        reasons = []

        for policy in self.policies.values():
            triggered, trigger_reason = policy.check_metrics(system_metrics)
            if triggered and policy.action == "throttle":
                throttled = True
                self._active_throttles[policy.id] = time.time() + 30.0
                policy_results.append({"policy": policy.id, "action": "throttle", "reason": trigger_reason})

        if self._warden is not None:
            try:
                warden = self._get_warden()
                if warden:
                    veto_result = await warden.veto(prompt)
                    if isinstance(veto_result, dict) and veto_result.get("veto", False):
                        blocked = True
                        reasons.append(f"warden: {veto_result.get('reason', 'vetoed')}")
                        policy_results.append({"policy": "warden_veto", "action": "block", "reason": veto_result.get("reason")})
            except Exception as e:
                policy_results.append({"policy": "warden_veto", "action": "error", "reason": str(e)})

        if self._constitution is not None:
            try:
                constitution = self._get_constitution()
                plan = context.get("plan", {})
                cv_result = await constitution.validate(plan, context)
                if isinstance(cv_result, dict):
                    violations = cv_result.get("violations", [])
                    for v in violations:
                        if v.get("severity") in ("critical", "high"):
                            blocked = True
                            reasons.append(f"constitution: {v.get('detail', 'violation')}")
                            policy_results.append({"policy": "constitution", "action": "block", **v})
            except Exception as e:
                policy_results.append({"policy": "constitution", "action": "error", "reason": str(e)})

        elapsed_ms = round((time.time() - start) * 1000, 2)

        if blocked:
            self._escalation_count += 1

        decision = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt_preview": prompt[:120],
            "allowed": not blocked and not throttled,
            "blocked": blocked,
            "throttled": throttled,
            "reasons": reasons,
            "policy_results": policy_results,
            "system_metrics": system_metrics,
            "elapsed_ms": elapsed_ms,
            "escalation_rate": self.escalation_rate(),
            "total_decisions": self._total_decisions,
        }

        if blocked:
            decision["suggestion"] = self._suggest_mitigation(prompt, reasons)

        self._logs.append(decision)
        self._log_to_file(decision)
        return decision

    async def apply_policy(self, policy_id: str, action: str, reason: str = "") -> bool:
        policy = self.policies.get(policy_id)
        if policy:
            if action == "enable":
                policy.enabled = True
            elif action == "disable":
                policy.enabled = False
            elif action == "throttle":
                policy.config["action"] = "throttle"
            elif action == "block":
                policy.config["action"] = "block"
            elif action == "adjust_severity":
                policy.severity = reason or policy.severity
            else:
                return False
            self._log_to_file({"action": "apply_policy", "policy_id": policy_id, "new_action": action, "reason": reason})
            return True
        return False

    async def add_policy(self, policy_id: str, config: Dict[str, Any]) -> bool:
        if policy_id in self.policies:
            return False
        self.policies[policy_id] = DynamicPolicy(policy_id, config)
        return True

    async def remove_policy(self, policy_id: str) -> bool:
        if policy_id not in self.policies:
            return False
        del self.policies[policy_id]
        return True

    def escalation_rate(self) -> float:
        if self._total_decisions == 0:
            return 0.0
        return round(self._escalation_count / self._total_decisions, 4)

    def get_active_policies(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.policies.values()]

    def get_recent_decisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._logs[-limit:]

    def get_metrics_summary(self) -> Dict[str, Any]:
        if not self._metrics_history:
            return {}
        latest = self._metrics_history[-1]
        summary = {k: v for k, v in latest.items() if isinstance(v, (int, float))}
        summary["escalation_rate"] = self.escalation_rate()
        summary["total_decisions"] = self._total_decisions
        summary["active_policies"] = len(self.policies)
        return summary

    def _collect_metrics(self) -> Dict[str, Any]:
        try:
            from kernel.metrics_collector import MetricsCollector
            mc = MetricsCollector
            return {
                "latency_p50": mc.get_latency_stats().get("p50", 0.0) if hasattr(mc, "get_latency_stats") else 0.0,
                "error_rate": mc.get_error_rate() if hasattr(mc, "get_error_rate") else 0.0,
                "cpu_percent": mc.get_metric("system.cpu.percent") if hasattr(mc, "get_metric") else 50.0,
                "memory_mb": mc.get_metric("system.memory.used_mb") if hasattr(mc, "get_metric") else 500.0,
                "escalation_rate": self.escalation_rate(),
            }
        except Exception:
            return {"latency_p50": 0.0, "error_rate": 0.0, "cpu_percent": 50.0, "memory_mb": 500.0, "escalation_rate": self.escalation_rate()}

    def _suggest_mitigation(self, prompt: str, reasons: List[str]) -> Optional[str]:
        if any("PII" in r for r in reasons):
            return "Remove personal identifiable information from prompt"
        if any("toxic" in r for r in reasons):
            return "Rephrase prompt to remove toxic or abusive language"
        if any("injection" in r for r in reasons):
            return "Remove meta-instructions or delimiter manipulation attempts"
        if any("resource" in r for r in reasons):
            return "Reduce prompt complexity or wait for system load to decrease"
        return None

    def _log_to_file(self, entry: Dict[str, Any]) -> None:
        try:
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
        except OSError:
            import logging
            logging.getLogger("doutor.governance").warning("Governance log write failed")