import asyncio, json, logging
from typing import Dict, List

logger = logging.getLogger("doutor.council")

class CouncilProtocol:
    def __init__(self, agents: Dict):
        self.agents = agents
        self.veto_threshold = 0.6

    async def convene(self, task_context: Dict, phase: str) -> Dict:
        opinions = []
        tasks = []
        for role, agent in self.agents.items():
            if role not in ["the_master_key", "the_lateral"]:
                tasks.append(self._get_opinion(agent, role, task_context, phase))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"[Council] Agent failed: {result}")
                continue
            opinions.append(result)

        rejects = [o for o in opinions if o.get("vote") == "reject"]
        approves = [o for o in opinions if o.get("vote") == "approve"]

        veto_rate = len(rejects) / len(opinions) if opinions else 0

        if veto_rate >= self.veto_threshold:
            return {
                "status": "vetoed",
                "reason": f"Council veto: {len(rejects)}/{len(opinions)} agents rejected",
                "opinions": opinions,
                "blocking_agents": [r["agent"] for r in rejects]
            }

        return {
            "status": "approved",
            "opinions": opinions,
            "consensus": "approve" if len(approves) > len(rejects) else "conditional",
            "warnings": [o.get("concern") for o in opinions if o.get("risk_flag") in ["medium", "high"]]
        }

    async def _get_opinion(self, agent, role: str, context: Dict, phase: str) -> Dict:
        prompt = f"""
FASE: {phase}
CONTEXTO: {json.dumps(context, default=str)[:1000]}

Voce e {role}. Sua opiniao e OBRIGATORIA e VINCULANTE.
Analise sob SUA PERSPECTIVA TECNICA e retorne JSON:
{{
  "agent": "{role}",
  "opinion": "string (analise tecnica objetiva)",
  "vote": "approve|conditional|reject",
  "risk_flag": "low|medium|high",
  "concern": "string (se houver)",
  "requirement": "string (o que precisa mudar para aprovar)"
}}

Regras:
- Se for risco de seguranca, dados ou infra critica -> REJECT
- Se for melhoria possivel mas nao bloqueante -> CONDITIONAL
- Se estiver dentro dos padroes -> APPROVE
- NUNCA seja condescendente. Sua opiniao importa.
"""
        try:
            result = await agent.execute(prompt, force_chronic=False)
            content = result.get("response", {}).get("content", "{}")
            return self._safe_json_parse(content)
        except Exception as e:
            return {"agent": role, "vote": "reject", "opinion": f"Agent error: {str(e)}", "risk_flag": "high"}

    def _safe_json_parse(self, text: str) -> Dict:
        import re
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        clean = match.group(1) if match else text
        try:
            return json.loads(clean)
        except:
            return {"vote": "reject", "opinion": "Invalid JSON response", "risk_flag": "high"}

print('agents/council_protocol.py entregue. Veto real com threshold de 60%.')
