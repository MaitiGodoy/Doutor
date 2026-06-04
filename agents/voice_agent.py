import json, logging
from typing import Dict
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.voice")

class VoiceAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_voice", config, router)

    async def execute(self, prompt: str, force_chronic: bool = False) -> Dict:
        system = "You are The Voice — a brand tone specialist who ensures all copy and communication aligns with brand voice and personality."
        result = await self._call_llm(system, prompt, force_chronic)
        content = result.get("response", {}).get("content", "{}")
        try:
            return json.loads(content) if isinstance(content, str) else content
        except:
            return {"voice": content, "raw": True}
