import json, logging
from typing import Dict
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.zoiao")

class ZoiaoAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_zoiao", config, router)

    async def execute(self, prompt: str, force_chronic: bool = False) -> Dict:
        system = "You are Zoiao — the raw, uncensored debug agent who inspects internals, runs diagnostics, and exposes hidden system state."
        result = await self._call_llm(system, prompt, force_chronic)
        content = result.get("response", {}).get("content", "{}")
        try:
            return json.loads(content) if isinstance(content, str) else content
        except:
            return {"diagnostic": content, "raw": True}
