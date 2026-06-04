from agents.base_agent import BaseAgent

class MinimalistAgent(BaseAgent):
    def __init__(self, config, router):
        super().__init__("the_minimalist", config, router)

    async def optimize_task(self, task: dict) -> dict:
        prompt = f"Otimize esta tarefa para reduzir tokens/tempo sem perder qualidade: {task}. JSON: {{'optimization': str, 'savings_pct': int}}"
        result = await self.execute(prompt, force_chronic=False)
        if isinstance(result, dict):
            return {"optimization": result.get("optimization", ""), "savings_pct": int(result.get("savings_pct", 0))}
        return {"optimization": "", "savings_pct": 0}
