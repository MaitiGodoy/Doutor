"""
Autonomous Agent Loop — ReAct + Reflexion core v5.1.
Integrates provider_router, guards, sandbox, scaler, memory_store, metrics_collector.
Confidence decay: -0.2 error, +0.1 success. Escalate if confidence < 0.3.
Dry-run obrigatório para ações que modificam estado.
Zero stubs. 100% funcional e assíncrono.
"""

import json
import time
import uuid
import asyncio
import logging
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field

from kernel.provider_router import get_provider_router
from kernel.guards import SecurityGuard
from kernel.sandbox import NemoClawSandbox
from kernel.scaler import CuOptResourceScaler
from kernel.memory_store import MemoryStore
from kernel.metrics_collector import MetricsCollector

logger = logging.getLogger("agent_loop")
LOG_PATH = Path(__file__).resolve().parents[3] / "logs" / "autonomy.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class AgentContext:
    """Contexto persistente de um ciclo autônomo."""
    goal: str = ""
    history: list = field(default_factory=list)
    confidence: float = 1.0
    retries: int = 0
    max_retries: int = 3
    last_error: str = ""
    dry_run: bool = True
    chain_id: str = ""
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    observations: list = field(default_factory=list)
    plans: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    reflections: list = field(default_factory=list)
    escalations: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def touch(self):
        self.updated_at = time.time()

    @property
    def should_escalate(self) -> bool:
        return self.confidence < 0.3 or self.retries >= self.max_retries

    def adjust_confidence(self, success: bool):
        if success:
            self.confidence = min(1.0, self.confidence + 0.1)
        else:
            self.confidence = max(0.0, self.confidence - 0.2)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "goal": self.goal,
            "confidence": self.confidence,
            "retries": self.retries,
            "last_error": self.last_error,
            "dry_run": self.dry_run,
            "chain_id": self.chain_id,
            "steps": len(self.history),
            "observations": len(self.observations),
            "plans": len(self.plans),
            "actions": len(self.actions),
            "reflections": len(self.reflections),
            "escalations": len(self.escalations),
            "age_seconds": round(time.time() - self.created_at, 2),
        }


class AutonomousAgentLoop:
    """Loop autônomo ReAct + Reflexion.

    Ciclo: perceive -> plan -> act (dry-run se necessário) -> reflect -> escalate se necessário -> repeat.
    Confiança decai com erros, escala se abaixo do threshold.
    """

    def __init__(
        self,
        goal: str,
        max_iterations: int = 10,
        dry_run: bool = True,
        confidence_threshold: float = 0.3,
    ):
        self.ctx = AgentContext(goal=goal, dry_run=dry_run)
        self.max_iterations = max_iterations
        self.confidence_threshold = confidence_threshold
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.sandbox = NemoClawSandbox()
        self.scaler = CuOptResourceScaler()
        self.memory = MemoryStore()
        self.metrics = MetricsCollector()
        self.ctx.chain_id = self.metrics.start_chain(f"agent_loop_{self.ctx.run_id[:8]}")

    async def run_cycle(self) -> AgentContext:
        """Executa o ciclo autônomo completo.

        Returns:
            AgentContext com histórico de execução.
        """
        logger.info(f"Iniciando ciclo autônomo: goal={self.ctx.goal[:60]}... dry_run={self.ctx.dry_run}")

        for iteration in range(self.max_iterations):
            step = iteration + 1
            logger.info(f"[{step}/{self.max_iterations}] confidence={self.ctx.confidence:.2f}")

            start = time.time()

            try:
                await self._perceive()
                plan = await self._plan()
                actions = await self._act(plan)
                await self._reflect(actions)
            except Exception as e:
                self.ctx.last_error = str(e)
                self.ctx.adjust_confidence(success=False)
                self.ctx.history.append({"step": step, "status": "error", "error": str(e)})
                logger.error(f"[{step}] Error: {e}")
                continue

            latency = round((time.time() - start) * 1000, 2)
            self.metrics.chain_add_event(self.ctx.chain_id, "cycle_completed", {
                "step": step,
                "latency_ms": latency,
                "confidence": self.ctx.confidence,
            })

            self.ctx.touch()
            self._persist_log()

            if self.ctx.should_escalate:
                logger.warning(f"[{step}] Escalando — confidence={self.ctx.confidence:.2f}, retries={self.ctx.retries}")
                await self._escalate()
                break

        # Finaliza métricas
        status = "completed" if not self.ctx.should_escalate else "escalated"
        self.metrics.end_chain(self.ctx.chain_id, status=status)

        return self.ctx

    async def _perceive(self) -> None:
        """Observa o ambiente via provider_router + guarda em memória."""
        prompt = (
            f"Goal: {self.ctx.goal}\n"
            f"Context: {json.dumps(self.ctx.history[-3:] if self.ctx.history else [])}\n"
            "Provide observations relevant to this goal."
        )
        response = await self.router.route(prompt)

        obs = {"timestamp": time.time(), "prompt": prompt[:100], "response": str(response)[:500]}
        self.ctx.observations.append(obs)

        self.memory.append_event({
            "aggregate_id": self.ctx.run_id,
            "event_type": "agent_perceived",
            "data": obs,
        })

    async def _plan(self) -> list[dict]:
        """Cria plano de ação usando o LLM."""
        obs_summary = self.ctx.observations[-3:] if self.ctx.observations else []
        prompt = (
            f"Goal: {self.ctx.goal}\n"
            f"Recent observations: {json.dumps(obs_summary)}\n"
            f"Confidence: {self.ctx.confidence:.2f}\n"
            f"Retries: {self.ctx.retries}\n"
            "Generate a JSON plan: list of {'step': int, 'tool': str, 'args': dict, 'modifies_state': bool}"
        )

        raw = await self.router.route(prompt)

        try:
            plan = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(plan, dict) and "plan" in plan:
                plan = plan["plan"]
            if not isinstance(plan, list):
                plan = [{"step": 1, "tool": "noop", "args": {}, "modifies_state": False}]
        except (json.JSONDecodeError, TypeError):
            plan = [{"step": 1, "tool": "noop", "args": {}, "modifies_state": False}]

        entry = {"timestamp": time.time(), "plan": plan}
        self.ctx.plans.append(entry)

        self.memory.append_event({
            "aggregate_id": self.ctx.run_id,
            "event_type": "agent_planned",
            "data": {"plan_steps": len(plan)},
        })

        return plan

    async def _act(self, plan: list[dict]) -> list[dict]:
        """Executa o plano. Se modifies_state e dry_run, simula sem alterar estado."""
        action_results = []

        for action in plan:
            tool = action.get("tool", "noop")
            args = action.get("args", {})
            modifies_state = action.get("modifies_state", False)

            # Dry-run: ações que modificam estado são simuladas
            if modifies_state and self.ctx.dry_run:
                action_results.append({
                    "tool": tool,
                    "args": args,
                    "status": "dry_run",
                    "result": {"message": f"Dry-run: {tool} skipped (modifies state)"},
                })
                self.ctx.history.append({"step": len(self.ctx.history) + 1, "tool": tool, "status": "dry_run"})
                continue

            # Guard check
            if not self.guard.allow(tool, args):
                action_results.append({
                    "tool": tool,
                    "args": args,
                    "status": "blocked",
                    "result": {"error": "guard_denied"},
                })
                self.ctx.adjust_confidence(success=False)
                self.ctx.retries += 1
                continue

            # Sandbox execution
            result = self.sandbox.run(tool, **args)
            success = result.get("success", False) or result.get("status") == "ok"

            action_results.append({
                "tool": tool,
                "args": args,
                "status": "ok" if success else "error",
                "result": result,
            })

            self.ctx.adjust_confidence(success=success)
            if not success:
                self.ctx.retries += 1
                self.ctx.last_error = str(result.get("error", "unknown"))
            else:
                self.ctx.retries = 0

            self.ctx.history.append({
                "step": len(self.ctx.history) + 1,
                "tool": tool,
                "status": "ok" if success else "error",
            })

            self.metrics.record_llm_call(
                provider="sandbox",
                model=tool,
                tokens_in=len(json.dumps(args)),
                tokens_out=len(json.dumps(result)),
                latency_ms=0,
                chain_id=self.ctx.chain_id,
                status="success" if success else "error",
            )

        entry = {"timestamp": time.time(), "actions": action_results}
        self.ctx.actions.append(entry)

        self.memory.append_event({
            "aggregate_id": self.ctx.run_id,
            "event_type": "agent_acted",
            "data": {"actions_count": len(action_results)},
        })

        return action_results

    async def _reflect(self, actions: list[dict]) -> None:
        """Reflexão sobre resultados. Avalia erros e sugere ajustes."""
        if not actions:
            return

        prompt = (
            "Reflect on these action results. "
            "Output JSON: {'assessment': str, 'adjustments': list[str], 'confidence_delta': float}\n"
            + json.dumps(actions, ensure_ascii=False)
        )

        raw = await self.router.route(prompt)

        try:
            reflection = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            reflection = {"assessment": "parse_failed", "adjustments": [], "confidence_delta": 0.0}

        entry = {"timestamp": time.time(), "reflection": reflection}
        self.ctx.reflections.append(entry)

        # Ajuste extra de confiança via reflexão
        delta = reflection.get("confidence_delta", 0.0)
        if delta != 0.0:
            self.ctx.confidence = max(0.0, min(1.0, self.ctx.confidence + delta))

        self.memory.append_event({
            "aggregate_id": self.ctx.run_id,
            "event_type": "agent_reflected",
            "data": {"assessment": reflection.get("assessment", "")},
        })

    async def _escalate(self) -> None:
        """Escalada: registra contexto e notifica."""
        esc = {
            "timestamp": time.time(),
            "run_id": self.ctx.run_id,
            "goal": self.ctx.goal,
            "confidence": self.ctx.confidence,
            "retries": self.ctx.retries,
            "last_error": self.ctx.last_error,
            "reason": "confidence_threshold" if self.ctx.confidence < self.confidence_threshold else "max_retries",
            "summary": self.ctx.to_dict(),
        }
        self.ctx.escalations.append(esc)

        self.memory.append_event({
            "aggregate_id": self.ctx.run_id,
            "event_type": "agent_escalated",
            "data": esc,
        })

        self._persist_log()

    # ─── Dry-run toggle ────────────────────────────────────────

    def set_dry_run(self, enabled: bool):
        """Ativa/desativa dry-run mode."""
        self.ctx.dry_run = enabled
        logger.info(f"Dry-run mode: {enabled}")

    # ─── Persistence ──────────────────────────────────────────

    def _persist_log(self) -> None:
        """Append current context as JSONL to autonomy.jsonl."""
        try:
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(self.ctx.to_dict(), ensure_ascii=False) + "\n")
        except OSError:
            pass

    # ─── Sync entry point (para compatibilidade) ──────────────

    def run(self) -> AgentContext:
        """Versão síncrona do run_cycle para compatibilidade."""
        return asyncio.run(self.run_cycle())
