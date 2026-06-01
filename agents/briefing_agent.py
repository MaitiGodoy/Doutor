import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.briefing_agent")

DEFAULT_QUESTIONS = [
    {"key": "niche", "question": "Qual o nicho/mercado-alvo?", "type": "text", "required": True},
    {"key": "audience", "question": "Qual a audiência específica (idade, profissão, dores)?", "type": "text", "required": True},
    {"key": "goal", "question": "Qual o objetivo? (ex: waitlist, pre-sale, branding, lead gen)", "type": "text", "required": True},
    {"key": "platforms", "question": "Quais plataformas? (LinkedIn, Twitter, Email, Meta, Google)", "type": "multi", "required": False},
    {"key": "tone", "question": "Qual o tom? (técnico, casual, autoridade, disruptivo)", "type": "text", "required": False},
    {"key": "budget_limit", "question": "Qual o limite de budget diário (em USD)?", "type": "number", "required": False},
    {"key": "kpis", "question": "KPIs principais? (ctr, cvr, roas, engagement)", "type": "multi", "required": False},
    {"key": "competitors", "question": "Concorrentes para referência (separados por vírgula)", "type": "text", "required": False},
    {"key": "deadline", "question": "Prazo para entrega?", "type": "text", "required": False},
    {"key": "extra_notes", "question": "Observações extras ou requisitos especiais?", "type": "text", "required": False},
]


class BriefingAgent(BaseAgent):
    def __init__(self, config: Dict = None, router=None):
        super().__init__("the_scout", config or {}, router)
        self.questions = DEFAULT_QUESTIONS
        self.env_path = Path(".env")

    def _generate_question(self, q: Dict) -> str:
        if q["required"]:
            return f"[OBRIGATÓRIO] {q['question']}"
        return f"[OPCIONAL] {q['question']}"

    def _parse_response(self, responses: Dict[str, Any]) -> Dict:
        parsed = {}
        for q in self.questions:
            key = q["key"]
            val = responses.get(key, "")
            if q["type"] == "number":
                try:
                    parsed[key] = float(val) if val else 0.0
                except (ValueError, TypeError):
                    parsed[key] = 0.0
            elif q["type"] == "multi":
                if isinstance(val, str):
                    parsed[key] = [v.strip() for v in val.split(",") if v.strip()]
                elif isinstance(val, list):
                    parsed[key] = val
                else:
                    parsed[key] = []
            elif q["type"] == "text":
                parsed[key] = str(val) if val else ""
            else:
                parsed[key] = val
        return parsed

    async def collect_briefing(self, raw_input: Dict) -> Dict:
        start = time.time()
        questions_to_ask = []
        missing = []

        for q in self.questions:
            key = q["key"]
            existing = raw_input.get(key)
            if existing is not None and existing != "":
                continue
            if q["required"]:
                missing.append(q)
            questions_to_ask.append(self._generate_question(q))

        if missing:
            logger.info(f"Briefing missing {len(missing)} required fields. Questions generated.")

        parsed = self._parse_response(raw_input)
        self._save_to_env_secure(parsed)

        result = {
            "status": "complete",
            "briefing": parsed,
            "missing_required": [q["key"] for q in missing],
            "questions_count": len(questions_to_ask),
            "elapsed_ms": int((time.time() - start) * 1000),
        }
        self._log_execution({"mode": "collect_briefing", "result": result})
        return result

    def _save_to_env_secure(self, briefing: Dict):
        try:
            env_vars = {}
            if self.env_path.exists():
                for line in self.env_path.read_text(encoding="utf-8").split("\n"):
                    if "=" in line and not line.strip().startswith("#"):
                        k, v = line.strip().split("=", 1)
                        env_vars[k] = v

            for key, val in briefing.items():
                if val and isinstance(val, str):
                    env_key = f"BRIEFING_{key.upper()}"
                    env_vars[env_key] = str(val)

            with open(self.env_path, "w", encoding="utf-8") as f:
                for k, v in env_vars.items():
                    f.write(f"{k}={v}\n")
            logger.info(f"Briefing saved to .env ({len(briefing)} keys)")
        except Exception as e:
            logger.warning(f"Failed to save briefing to .env: {e}")
