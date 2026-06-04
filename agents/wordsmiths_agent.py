import json, logging
from typing import Dict
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.wordsmiths")

class WordsmithsAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_wordsmiths", config, router)

    async def execute(self, prompt: str, force_chronic: bool = False) -> Dict:
        system = "You are The Wordsmiths — expert copywriters who craft persuasive, high-converting text across all formats and platforms."
        result = await self._call_llm(system, prompt, force_chronic)
        content = result.get("response", {}).get("content", "{}")
        try:
            return json.loads(content) if isinstance(content, str) else content
        except:
            return {"copy": content, "raw": True}
