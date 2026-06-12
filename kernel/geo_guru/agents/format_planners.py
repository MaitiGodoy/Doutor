import asyncio
from typing import Dict, List

class GEO_FormatPlanners:
    def __init__(self):
        self.formats = {
            "alpha": "FAQ estruturado com schema",
            "beta": "Documento técnico open-source",
            "gamma": "Lista numerada com dados estruturados",
            "delta": "Artigo jornalístico com citações"
        }
    
    async def generate(self, context: Dict) -> Dict:
        """Gera planos A/B/C/D de formatos otimizados para IA"""
        plans = {}
        
        for plan_type, format_desc in self.formats.items():
            plans[plan_type] = await self._create_plan(plan_type, format_desc, context)
        
        # Seleciona winner baseado no contexto
        winner = await self._select_winner(plans, context)
        
        return {
            "plans": plans,
            "winner": winner,
            "rationale": f"Formato {winner} tem maior probabilidade de ser citado por IAs"
        }
    
    async def _create_plan(self, plan_type: str, format_desc: str, context: Dict) -> Dict:
        return {
            "type": plan_type,
            "format": format_desc,
            "estimated_impact": self._estimate_impact(plan_type, context),
            "effort_level": self._estimate_effort(plan_type),
            "timeline": "2-4 semanas",
            "schema_required": plan_type in ["alpha", "gamma"],
            "target_queries": context.get("target_queries", [])[:5]
        }
    
    def _estimate_impact(self, plan_type: str, context: Dict) -> float:
        # Mock de impacto baseado em tipo
        impacts = {"alpha": 0.85, "beta": 0.75, "gamma": 0.70, "delta": 0.65}
        return impacts.get(plan_type, 0.5)
    
    def _estimate_effort(self, plan_type: str) -> int:
        efforts = {"alpha": 4, "beta": 7, "gamma": 3, "delta": 5}
        return efforts.get(plan_type, 5)
    
    async def _select_winner(self, plans: Dict, context: Dict) -> str:
        # Seleciona por melhor ROI (impacto / esforço)
        best_roi = 0
        winner = "alpha"
        
        for plan_type, plan in plans.items():
            roi = plan["estimated_impact"] / max(plan["effort_level"], 1)
            if roi > best_roi:
                best_roi = roi
                winner = plan_type
        
        return winner