from agents.base_agent import BaseAgent

class DirectorAgent(BaseAgent):
    def __init__(self, config, router):
        super().__init__("the_director", config, router)

    async def approve_plan(self, plan: dict) -> dict:
        prompt = f"Aprove ou veto este plano macro: {plan}. Retorne JSON: {{'approved': bool, 'reason': str}}"
        result = await self.execute(prompt, force_chronic=False)
        if isinstance(result, dict):
            return {"approved": result.get("approved", False), "reason": result.get("reason", "")}
        return {"approved": False, "reason": "failed_to_parse"}
