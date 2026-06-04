import json, logging
from typing import Dict
from agents.base_agent import BaseAgent
from departments.seo_engine import SEOEngine

logger = logging.getLogger("doutor.ranker")

class RankerAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_ranker", config, router)
        self.seo = SEOEngine()

    async def execute(self, prompt: str, force_chronic: bool = False) -> Dict:
        system = "You are The Ranker — an SEO specialist who optimizes content and structure for search engines and organic traffic."
        result = await self._call_llm(system, prompt, force_chronic)
        content = result.get("response", {}).get("content", "{}")
        try:
            return json.loads(content) if isinstance(content, str) else content
        except:
            return {"seo": content, "raw": True}

    def optimize_file(self, file_path: str) -> Dict:
        return self.seo.optimize_file(file_path)
