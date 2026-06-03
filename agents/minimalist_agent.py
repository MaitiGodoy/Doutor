import os, json, time
from pathlib import Path
from typing import Dict, Any
from agents.base_agent import BaseAgent

class MinimalistAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_minimalist", config, router)
        self.log_path = Path(config.get("log_path", "logs/minimalist_optimizations.jsonl"))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    async def evaluate_optimization(self, task_description: str, current_context: Dict) -> Dict:
        prompt = f"""
Tarefa: {task_description}
Contexto Atual: {json.dumps(current_context, default=str)[:1000]}

Avalie se existe uma otimização de eficiência (menos tokens/tempo/código) sem perder qualidade.
Retorne APENAS JSON conforme schema.
"""
        result = await self.execute(prompt, force_chronic=False)
        parsed = self._safe_json_parse(result["response"]["content"])
        self._log_optimization(parsed)
        return parsed

    def _safe_json_parse(self, text: str) -> Dict:
        import re
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        clean = match.group(1) if match else text
        try:
            return json.loads(clean)
        except:
            return {"optimization": "none", "reason": "json_parse_error"}

    def _log_optimization(self, data: Dict):
        entry = {
            "timestamp": time.time(),
            "optimization": data.get("optimization"),
            "savings": data.get("savings"),
            "risk": data.get("risk_level")
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    async def apply_optimization(self, original_input: Dict, optimization_hint: str) -> Dict:
        # Lógica simples de aplicação: injeta hint no contexto para o próximo agente usar
        optimized_input = {**original_input, "optimization_applied": optimization_hint}
        return optimized_input