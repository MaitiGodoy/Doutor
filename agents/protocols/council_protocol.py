import asyncio, json
from typing import Dict, List

class CouncilProtocol:
    """Gerencia a Mesa Redonda onde todos os agentes opinam."""
    
    def __init__(self, agents: Dict, state_mgr):
        self.agents = agents
        self.state_mgr = state_mgr
        
    async def run_council_round(self, task_input: Dict) -> Dict:
        """Chama todos os agentes para opinar sobre a tarefa."""
        print("[CONSELHO] Iniciando rodada de opiniões obrigatórias...")
        
        opinions = []
        tasks = []
        
        # Chama todos os agentes em paralelo (ou sequencial se limite de tokens)
        for role, agent in self.agents.items():
            # Pula agentes de infraestrutura pura se necessário, mas idealmente TODOS falam
            if role in ['the_master_key', 'the_lateral']: continue # Estes agem, não opinam
            
            tasks.append(self._get_agent_opinion(agent, role, task_input))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                opinions.append({"agent": "unknown", "opinion": "error", "vote": "abstain"})
            else:
                opinions.append(result)
        
        # Síntese do Conselho
        synthesis = await self._synthesize_opinions(opinions, task_input)
        
        return {
            "council_active": True,
            "opinions": opinions,
            "synthesis": synthesis,
            "consensus": synthesis.get("consensus", "divergent")
        }

    async def _get_agent_opinion(self, agent, role: str, task: Dict) -> Dict:
        # Força o agente a opinar baseado na LENTE dele, mesmo fora da área
        prompt = f"""
TAREFA ATUAL: {json.dumps(task, default=str)[:500]}

Você é {role}. Mesmo que esta tarefa não seja sua especialidade direta, 
analise-a através da SUA LENTE e dê um parecer obrigatório.
Ex: Se você é Design e a tarefa é Backend, fale sobre estrutura de dados que impacta UI.
Se você é SEO e a tarefa é Copy, fale sobre densidade de palavras.

Responda APENAS JSON:
{
  "agent_role": "{role}",
  "lens_applied": "string (como você olhou pra isso)",
  "opinion": "string (sua contribuição crítica)",
  "risk_flag": "low|medium|high",
  "vote": "approve|conditional|reject",
  "suggestion": "string (melhoria rápida)"
}
"""
        try:
            result = await agent.execute(prompt, force_chronic=False) # Chronic não atrapalha a seriedade aqui
            content = result.get("response", {}).get("content", "{}")
            return json.loads(content) if isinstance(content, str) else content
        except:
            return {"agent_role": role, "opinion": "silent", "vote": "abstain"}

    async def _synthesize_opinions(self, opinions: List, task: Dict) -> Dict:
        # Usa o Orchestrator ou um modelo rápido para resumir o consenso
        # Simplificação: Retorna o raw para o Orchestrator usar
        return {
            "total_voters": len(opinions),
            "approvals": len([o for o in opinions if o.get("vote") == "approve"]),
            "risks_raised": [o.get("suggestion") for o in opinions if o.get("risk_flag") == "high"],
            "consensus": "approved" if len([o for o in opinions if o.get("vote") != "approve"]) < 3 else "debate_needed"
        }