"""
Autonomous Agent Loop – ReAct + Reflexion core.
Integrates provider_router, guards, sandbox, scaler.
Persists state via AgentContext (Pydantic v2) and logs to logs/autonomy.jsonl.
"""
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

# Kernel integrations
from kernel.provider_router import get_provider_router
from kernel.guards import SecurityGuard
from kernel.sandbox import NemoClawSandbox
from kernel.scaler import CuOptResourceScaler


LOG_PATH = Path(__file__).resolve().parents[4] / "logs" / "autonomy.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class AgentContext(BaseModel):
    """Persistent context for a single autonomous run."""
    model_config = ConfigDict(extra="allow")

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    goal: str = ""
    observations: List[Dict[str, Any]] = Field(default_factory=list)
    plans: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    reflections: List[Dict[str, Any]] = Field(default_factory=list)
    escalations: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = time.time()


class AutonomousAgentLoop:
    """
    ReAct + Reflexion autonomous loop.
    Cycle: perceive -> plan -> act -> reflect -> (escalate if needed) -> repeat.
    """

    def __init__(self, goal: str, max_iterations: int = 10):
        self.ctx = AgentContext(goal=goal)
        self.max_iterations = max_iterations
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.sandbox = NemoClawSandbox()
        self.scaler = CuOptResourceScaler()

    # ---------- Public API ----------
    def run(self) -> AgentContext:
        """Execute the autonomous loop up to max_iterations."""
        for _ in range(self.max_iterations):
            self._perceive()
            self._plan()
            self._act()
            self._reflect()
            if self._should_escalate():
                self._escalate()
                break
            self.ctx.touch()
            self._persist_log()
        return self.ctx

    # ---------- Core Steps ----------
    def _perceive(self) -> None:
        """Gather environment observations via provider router."""
        prompt = f"Observations for goal: {self.ctx.goal}"
        response = self.router.complete(prompt, temperature=0.2)
        obs = {"timestamp": time.time(), "prompt": prompt, "response": response}
        self.ctx.observations.append(obs)

    def _plan(self) -> None:
        """Create a step‑by‑step plan using the LLM."""
        prompt = (
            f"Goal: {self.ctx.goal}\n"
            f"Recent observations: {self.ctx.observations[-3:]}\n"
            "Produce a concise JSON plan with fields: step, tool, args."
        )
        raw = self.router.complete(prompt, temperature=0.3)
        try:
            plan = json.loads(raw)
        except json.JSONDecodeError:
            plan = [{"step": 1, "tool": "noop", "args": {}}]
        self.ctx.plans.append({"timestamp": time.time(), "plan": plan})

    def _act(self) -> None:
        """Execute the latest plan inside the sandbox, guarded by security."""
        latest_plan = self.ctx.plans[-1]["plan"]
        for action in latest_plan:
            tool = action.get("tool")
            args = action.get("args", {})
            # Guard check
            if not self.guard.allow(tool, args):
                self.ctx.actions.append(
                    {
                        "timestamp": time.time(),
                        "tool": tool,
                        "args": args,
                        "status": "blocked",
                        "reason": "guard_denied",
                    }
                )
                continue
            # Sandbox execution
            result = self.sandbox.run(tool, **args)
            self.ctx.actions.append(
                {
                    "timestamp": time.time(),
                    "tool": tool,
                    "args": args,
                    "status": "ok" if result.get("success") else "error",
                    "result": result,
                }
            )

    def _reflect(self) -> None:
        """Reflexion: evaluate outcomes, adjust future behaviour."""
        recent_actions = self.ctx.actions[-5:]
        prompt = (
            "Reflect on the following actions and results. "
            "Identify mistakes, suggest corrections, output JSON with fields: "
            "assessment, suggested_adjustments."
        )
        prompt += "\n" + json.dumps(recent_actions, ensure_ascii=False)
        raw = self.router.complete(prompt, temperature=0.4)
        try:
            reflection = json.loads(raw)
        except json.JSONDecodeError:
            reflection = {"assessment": "parse_failed", "suggested_adjustments": []}
        self.ctx.reflections.append({"timestamp": time.time(), "reflection": reflection})

    def _should_escalate(self) -> bool:
        """Decide whether to hand off to human / higher‑level orchestrator."""
        last_reflection = self.ctx.reflections[-1]["reflection"] if self.ctx.reflections else {}
        return last_reflection.get("assessment") in {"critical_failure", "deadlock"}

    def _escalate(self) -> None:
        """Create an escalation record and optionally notify operators."""
        esc = {
            "timestamp": time.time(),
            "run_id": self.ctx.run_id,
            "goal": self.ctx.goal,
            "reason": self.ctx.reflections[-1]["reflection"].get("assessment"),
            "context_snapshot": self.ctx.model_dump(),
        }
        self.ctx.escalations.append(esc)
        # In a real system this would push to a queue / alerting system.
        # Here we just persist it.
        self._persist_log()

    # ---------- Persistence ----------
    def _persist_log(self) -> None:
        """Append current context as a JSON line to autonomy.jsonl."""
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(self.ctx.model_dump_json() + "\n")
