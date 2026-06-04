from agents.base_agent import BaseAgent

class SeniorDevAgent(BaseAgent):
    def __init__(self, config, router):
        super().__init__("the_senior_dev", config, router)

    async def generate_code(self, spec: dict) -> dict:
        prompt = f"Gere código production-ready para: {spec}. Retorne JSON: {{'files': {{'path': 'content'}}}}"
        result = await self.execute(prompt, force_chronic=False)
        if isinstance(result, dict):
            return {"files": result.get("files", {})}
        return {"files": {}}
