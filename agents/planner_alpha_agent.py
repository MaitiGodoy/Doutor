from agents.base_agent import BaseAgent
import logging

logger = logging.getLogger("doutor.planner_alpha")

class PlannerAlphaAgent(BaseAgent):
    def __init__(self, config, router):
        super().__init__("the_planner_alpha", config, router)

    async def generate_plan(self, context: dict) -> dict:
        prompt = (
            f"Gere plano Alpha baseado em: {context}. "
            "Retorne JSON com: steps (list), dependencies (list), risk_level (str, 'low'), rollback_plan (str). "
            "Priorize caminhos testados e risco zero."
        )
        result = await self.execute(prompt, force_chronic=False)
        content = result.get("response", result)
        if isinstance(content, dict) and "content" in content:
            content = content["content"]
        return self._safe_json_parse(str(content))

# log marker - no emoji
