import json, logging
from typing import Dict
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.strategy")

class StrategyAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_architect", config, router)

    async def execute(self, prompt: str, force_chronic: bool = False) -> Dict:
        system = "You are The Architect — a strategic planner who designs robust, scalable system architecture and technical roadmaps."
        result = await self._call_llm(system, prompt, force_chronic)
        content = result.get("response", {}).get("content", "{}")
        try:
            return json.loads(content) if isinstance(content, str) else content
        except:
            return {"plan": content, "raw": True}
