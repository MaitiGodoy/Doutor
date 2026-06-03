import os, json, time, random
from pathlib import Path
from typing import Dict, List
from agents.base_agent import BaseAgent

class DarwinAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_darwin", config, router)
        self.log_path = Path(config.get("log_path", "logs/evolution.jsonl"))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    async def analyze_and_mutate(self, agent_logs: List[Dict], current_config: Dict) -> Dict:
        """Analisa logs de custo/erro e sugere mutação de prompt."""
        prompt = f"""
Analise os últimos logs de desempenho do agente '{current_config['role']}'.
Métricas: {json.dumps(agent_logs[-10:], default=str)[:1000]}
Config Atual: {json.dumps(current_config, default=str)}

Tarefa:
1. Identifique ineficiências (tokens altos para tarefas simples, erros recorrentes).
2. Gere UMA mutação do prompt ou config que reduza custo em >20% ou aumente precisão.
3. Retorne JSON com o novo prompt/config e a justificativa.

Exemplo Output:
{
  "mutation_type": "prompt_refinement",
  "new_prompt_section": "string (nova instrução otimizada)",
  "reason": "string (por que vai economizar)",
  "estimated_savings_pct": 25
}
"""
        result = await self.execute(prompt, force_chronic=False)
        return self._safe_json_parse(result["response"]["content"])

    def _safe_json_parse(self, text: str) -> Dict:
        import re
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        clean = match.group(1) if match else text
        try: return json.loads(clean)
        except: return {"error": "parse_fail"}

    def _log_mutation(self, mutation: Dict):
        entry = {
            "timestamp": time.time(),
            "agent_role": self.role,
            "mutation": mutation
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")