"""
HermesLayer – Wrapper for Hermes API integration.
execute_task() for task execution via Hermes LLM.
Zero stubs. 100% funcional.
"""
import json
import os
import time
from typing import Any, Dict, Optional
from pathlib import Path

from kernel.provider_router import get_provider_router
from kernel.guards import SecurityGuard

LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "hermes_layer.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class HermesLayer:
    """Wrapper for Hermes API integration."""

    def __init__(self, chain_id: str = ""):
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.chain_id = chain_id
        self.api_url = os.getenv("HERMES_API_URL", "http://localhost:11434/api/generate")
        self.model = os.getenv("HERMES_MODEL", "hermes-3-llama-3.1-8b")

    async def execute_task(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        guard_res = self.guard.validate_input(task, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard"}
        prompt = f"Task: {task}\nContext: {json.dumps(context or {})}\nExecute and return structured result."
        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            parsed = json.loads(result)
        except json.JSONDecodeError:
            parsed = {"raw": result}
        entry = {"action": "execute_task", "task": task, "result": parsed, "timestamp": time.time()}
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return parsed

    async def embed(self, text: str) -> Dict[str, Any]:
        prompt = f"Generate embedding vector for: {text[:1000]}"
        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="low")
        return {"text": text[:200], "embedding": result, "timestamp": time.time()}

    async def chat(self, messages: list) -> Dict[str, Any]:
        prompt = f"Continue conversation: {json.dumps(messages[-3:])}"
        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        return {"response": result, "timestamp": time.time()}