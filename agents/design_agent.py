import json, logging
from typing import Dict
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.design")

class DesignAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_empath", config, router)

    async def execute(self, prompt: str, force_chronic: bool = False) -> Dict:
        system = "You are The Empath — a UX/design specialist who crafts intuitive, accessible, and emotionally resonant user experiences."
        result = await self._call_llm(system, prompt, force_chronic)
        content = result.get("response", {}).get("content", "{}")
        try:
            return json.loads(content) if isinstance(content, str) else content
        except:
            return {"design": content, "raw": True}
