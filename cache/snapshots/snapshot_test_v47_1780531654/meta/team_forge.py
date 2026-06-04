import json
from pathlib import Path
from typing import Dict, List, Optional


class TeamForge:
    def __init__(self):
        self.roles_dir = Path("agents/roles")

    def generate_context(self, briefing: Dict) -> Dict:
        niche = briefing.get("niche", "general").lower()
        audience = briefing.get("audience", "general")
        goal = briefing.get("goal", "awareness").lower()

        critical_roles = self._resolve_critical_roles(niche, goal)

        context_prompt = self._build_context_prompt(briefing, critical_roles)

        priority_bias = self._resolve_priority_bias(goal)

        return {
            "mode": "team_forge_context",
            "briefing_summary": {
                "niche": niche,
                "audience": audience,
                "goal": goal,
            },
            "critical_roles": critical_roles,
            "context_prompt": context_prompt,
            "priority_bias": priority_bias,
            "role_count": len(critical_roles),
        }

    def _resolve_critical_roles(self, niche: str, goal: str) -> List[Dict]:
        base_roles = [
            {"role": "the_scout", "priority": "high", "reason": "Briefing e pesquisa de mercado"},
            {"role": "the_polymath", "priority": "high", "reason": "Inteligência e síntese de dados"},
            {"role": "the_architect", "priority": "high", "reason": "Estratégia e arquitetura"},
            {"role": "the_constitution", "priority": "medium", "reason": "Governança macro"},
            {"role": "the_wordsmiths", "priority": "high", "reason": "Criação de copy"},
            {"role": "the_voice", "priority": "medium", "reason": "Voz e tom"},
        ]

        if "infoproduto" in niche or "curso" in niche:
            base_roles.append({"role": "the_producer", "priority": "high", "reason": "Produção de infoproduto"})
        if "code" in niche or "programming" in niche or "tecnologia" in niche:
            base_roles.append({"role": "the_senior_dev", "priority": "high", "reason": "Código técnico"})
        if "venda" in goal or "conversion" in goal or "sales" in goal or "pre-sale" in goal:
            base_roles.extend([
                {"role": "the_closer", "priority": "high", "reason": "Copy de conversão"},
                {"role": "the_scaler", "priority": "medium", "reason": "Otimização de conversão"},
            ])

        return base_roles

    def _build_context_prompt(self, briefing: Dict, critical_roles: List[Dict]) -> str:
        role_names = [r["role"] for r in critical_roles]
        return (
            f"Projeto para nicho '{briefing.get('niche', 'N/A')}', "
            f"audiência '{briefing.get('audience', 'N/A')}', "
            f"objetivo '{briefing.get('goal', 'N/A')}'. "
            f"Equipe alocada: {', '.join(role_names)}. "
            f"Produzir output alinhado ao tom '{briefing.get('tone', 'profissional')}' "
            f"para plataformas: {briefing.get('platforms', ['web'])}."
        )

    def _resolve_priority_bias(self, goal: str) -> Dict:
        biases = {
            "authority": 0.3,
            "conversion": 0.5,
            "engagement": 0.2,
            "virality": 0.3,
            "education": 0.4,
            "branding": 0.2,
        }
        for key in biases:
            if key in goal:
                return {
                    "bias": key,
                    "weight": biases[key],
                    "note": f"Viés para {key} ativado com peso {biases[key]}",
                }
        return {"bias": "balanced", "weight": 0.0, "note": "Viés neutro — todas as prioridades iguais"}
