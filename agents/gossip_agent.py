from agents.base_agent import BaseAgent

class GossipAgent(BaseAgent):
    def __init__(self, config, router):
        super().__init__("the_gossip", config, router)

    async def narrate_run(self, run_log: dict) -> dict:
        prompt = f"Narre os bastidores desta execução em pt-BR estilo fofoca técnica: {run_log}. JSON: {{'narrative_markdown': str, 'technical_summary': dict}}"
        result = await self.execute(prompt, force_chronic=False)
        if isinstance(result, dict):
            return {"narrative_markdown": result.get("narrative_markdown", ""), "technical_summary": result.get("technical_summary", {})}
        return {"narrative_markdown": "", "technical_summary": {}}
