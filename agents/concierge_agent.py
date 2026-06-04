import json, logging
from typing import Dict
from agents.base_agent import BaseAgent
from kernel.concierge import concierge_explain

logger = logging.getLogger("doutor.concierge")

class ConciergeAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_concierge", config, router)

    async def execute(self, prompt: str, force_chronic: bool = False) -> Dict:
        system = "You are The Concierge — the user-facing interface agent who translates complex system outputs into clear, actionable human language."
        result = await self._call_llm(system, prompt, force_chronic)
        content = result.get("response", {}).get("content", "{}")
        try:
            return json.loads(content) if isinstance(content, str) else content
        except:
            return {"concierge": content, "raw": True}
