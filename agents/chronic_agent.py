import json, logging
from typing import Dict
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.chronic")

class ChronicAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_chronic", config, router)

    async def execute(self, prompt: str, force_chronic: bool = True) -> Dict:
        system = "You are The Chronic — the long-context memory agent who retains and recalls extended conversation history and project context."
        result = await self._call_llm(system, prompt, force_chronic)
        content = result.get("response", {}).get("content", "{}")
        try:
            return json.loads(content) if isinstance(content, str) else content
        except:
            return {"memory": content, "raw": True}
