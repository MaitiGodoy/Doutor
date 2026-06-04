from agents.base_agent import BaseAgent
import logging

logger = logging.getLogger("doutor.senior_dev_core")

class SeniorDevCoreAgent(BaseAgent):
    def __init__(self, config, router):
        super().__init__("the_senior_dev_core", config, router)

    async def generate_code(self, plan: dict, context: dict) -> dict:
        prompt = (
            f"Gere código Core (backend/dados) para o plano: {plan}. "
            f"Contexto adicional: {context}. "
            "Retorne JSON com: files (dict path->content), tests (str). "
            "Código testável, trata erros, escala horizontalmente."
        )
        result = await self.execute(prompt, force_chronic=False)
        content = result.get("response", result)
        if isinstance(content, dict) and "content" in content:
            content = content["content"]
        return self._safe_json_parse(str(content))

# log marker - no emoji
