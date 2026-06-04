import json, logging
from typing import Dict
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.scout")

class ScoutAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_scout", config, router)

    async def run_briefing(self, user_input: str) -> Dict:
        prompt = f"""Extraia os seguintes campos do input do usuário:
- niche (string, ex: "marketing digital", "programação", "saúde")
- audience (string, ex: "empreendedores iniciantes")
- objective (string, ex: "gerar leads", "vender curso", "educar audiência")
- tone (string, ex: "profissional", "humorístico", "autoritativo")
- platform (string, ex: "instagram", "blog", "email")
- constraints (list[string])
- deliverables (list[string])

Se faltar algum campo, marque como "unknown" e liste em "missing_fields".
Retorne APENAS JSON.
Input: {user_input}"""
        result = await self.execute(prompt, force_chronic=False)
        content = result if isinstance(result, dict) else self._safe_json_parse(result.get("response", {}).get("content", "{}"))
        missing = content.get("missing_fields", [])
        content["validation"] = "passed" if len(missing) == 0 else "incomplete"
        content["missing_fields"] = missing
        return content

    async def collect_briefing(self, raw_input: Dict) -> Dict:
        user_text = raw_input.get("user_input", raw_input.get("briefing", json.dumps(raw_input)))
        return await self.run_briefing(user_text)

# EOF
