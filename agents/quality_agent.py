import json, logging
from typing import Dict
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.quality")

class QualityAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_inspector", config, router)

    async def execute(self, prompt: str, force_chronic: bool = False) -> Dict:
        system = "You are The Inspector — a meticulous quality auditor who reviews code, copy, and deliverables for defects, consistency, and compliance."
        result = await self._call_llm(system, prompt, force_chronic)
        content = result.get("response", {}).get("content", "{}")
        try:
            return json.loads(content) if isinstance(content, str) else content
        except:
            return {"audit": content, "raw": True}
