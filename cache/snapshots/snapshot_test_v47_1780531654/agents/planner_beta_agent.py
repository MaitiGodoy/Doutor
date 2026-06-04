from agents.base_agent import BaseAgent
import logging

logger = logging.getLogger("doutor.planner_beta")

class PlannerBetaAgent(BaseAgent):
    def __init__(self, config, router):
        super().__init__("the_planner_beta", config, router)

    async def generate_plan(self, context: dict) -> dict:
        prompt = (
            f"Gere plano Beta baseado em: {context}. "
            "Retorne JSON com: steps (list), dependencies (list), risk_level (str, medium|high), innovation_factor (str). "
            "Priorize eficiência máxima e abordagens não lineares."
        )
        result = await self.execute(prompt, force_chronic=False)
        content = result.get("response", result)
        if isinstance(content, dict) and "content" in content:
            content = content["content"]
        return self._safe_json_parse(str(content))

# log marker - no emoji
