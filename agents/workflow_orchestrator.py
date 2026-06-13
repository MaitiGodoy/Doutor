"""
WorkflowOrchestrator – Multi-agent workflow orchestration.
CrewAI-style sequential/hierarchical agent flows.
Zero stubs. 100% funcional.
"""
import asyncio
import json
import time
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path

from kernel.provider_router import get_provider_router
from kernel.guards import SecurityGuard

LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "workflow_orchestrator.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class WorkflowOrchestrator:
    """Orchestrates multi-agent workflows."""

    def __init__(self, chain_id: str = ""):
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.chain_id = chain_id

    async def sequential_flow(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        context = {}
        for step in steps:
            agent = step.get("agent", "default")
            task = step.get("task", "")
            prompt = f"Agent: {agent}\nTask: {task}\nContext: {json.dumps(context)}\nReturn structured result."
            guard_res = self.guard.validate_input(prompt, context={"chain_id": self.chain_id})
            if guard_res.status == "blocked":
                results.append({"step": agent, "error": "blocked"})
                break
            result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
            try:
                parsed = json.loads(result)
            except json.JSONDecodeError:
                parsed = {"raw": result}
            context.update({f"{agent}_result": parsed})
            results.append({"step": agent, "task": task, "result": parsed})
        entry = {"action": "sequential_flow", "steps": len(steps), "results": len(results), "timestamp": time.time()}
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return results

    async def hierarchical_flow(self, manager_task: str, agent_tasks: Dict[str, str]) -> Dict[str, Any]:
        prompt = f"Manager task: {manager_task}\nDelegate to: {json.dumps(agent_tasks)}\nCoordinate and return merged result."
        guard_res = self.guard.validate_input(prompt, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked"}
        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            parsed = {"raw": result}
        entry = {"action": "hierarchical_flow", "manager": manager_task, "agents": list(agent_tasks.keys()), "timestamp": time.time()}
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return parsed

    async def parallel_flow(self, tasks: List[str]) -> List[Any]:
        async def run(t: str) -> Any:
            r = await self.router.route(t, context={"chain_id": self.chain_id}, priority="normal")
            try:
                return json.loads(r)
            except json.JSONDecodeError:
                return {"raw": r}
        results = await asyncio.gather(*[run(t) for t in tasks])
        entry = {"action": "parallel_flow", "tasks": len(tasks), "timestamp": time.time()}
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return list(results)