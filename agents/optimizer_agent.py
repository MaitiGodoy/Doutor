import json, logging
from typing import Dict
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.optimizer")

class OptimizerAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_scaler", config, router)

    async def execute(self, prompt: str, force_chronic: bool = False) -> Dict:
        system = "You are The Scaler — a performance optimizer who refines code, infrastructure, and processes for speed, efficiency, and scale."
        result = await self._call_llm(system, prompt, force_chronic)
        content = result.get("response", {}).get("content", "{}")
        try:
            return json.loads(content) if isinstance(content, str) else content
        except:
            return {"optimization": content, "raw": True}
