import os, json, time
from pathlib import Path
from typing import Dict, Any, List
from agents.base_agent import BaseAgent

class GossipAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_gossip", config, router)
        self.log_path = Path(config.get("log_path", "logs/gossip_narratives.jsonl"))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    async def narrate_pipeline(self, pipeline_log: Dict, audit_trail: List[Dict], metrics: Dict) -> Dict:
        prompt = f"""
Você é A Fofoqueira. Narre os bastidores desta execução do Doutor.

CONTEXTO DA TAREFA:
{json.dumps(pipeline_log.get("input", {}), default=str)[:800]}

REGISTROS DE INTERAÇÃO (audit_trail):
{json.dumps(audit_trail[-20:], default=str)[:2000]}  # Últimas 20 entradas

MÉTRICAS:
{json.dumps(metrics, default=str)}

Gere a narrativa em português, estilo fofoca divertida, seguindo o schema.
Retorne APENAS JSON com "narrative_markdown" e "technical_summary".
"""
        result = await self.execute(prompt, force_chronic=False)
        parsed = self._safe_json_parse(result["response"]["content"])
        self._log_narrative(parsed)
        return parsed

    def _safe_json_parse(self, text: str) -> Dict:
        import re
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        clean = match.group(1) if match else text
        try:
            return json.loads(clean)
        except:
            return {
                "narrative_markdown": "🤫 Ops, a Fofoqueira travou. Mas resumo rápido: execução concluída.",
                "technical_summary": {"error": "narrative_parse_failed", "raw": clean[:200]}
            }

    def _log_narrative(self, data: Dict):
        entry = {
            "timestamp": time.time(),
            "narrative_preview": data.get("narrative_markdown", "")[:200],
            "tokens_used": data.get("technical_summary", {}).get("tokens_used"),
            "phases_count": len(data.get("technical_summary", {}).get("phases_executed", []))
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    async def send_to_concierge(self, narrative: Dict, user_phone: str) -> bool:
        # Envia narrativa formatada via Concierge (WhatsApp/Telegram)
        # Implementação simplificada: retorna True se sucesso
        message = narrative.get("narrative_markdown", "")
        if len(message) > 1000:
            message = message[:997] + "..."
        # Aqui entraria a chamada real para Twilio/WhatsApp
        print(f"[Fofoqueira] Enviando para {user_phone}: {message[:100]}...")
        return True