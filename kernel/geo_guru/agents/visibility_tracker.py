import asyncio
from typing import Dict, List

class GEO_VisibilityTracker:
    def __init__(self):
        self.ai_platforms = ["Perplexity", "ChatGPT", "Gemini", "Claude", "You.com"]
    
    async def measure(self, brand: str, content: str) -> Dict:
        """Mede visibilidade em AI SERPs"""
        # Mock de medição (em produção: APIs de scraping ou parcerias)
        positions = {}
        
        for platform in self.ai_platforms:
            # Simula posição (em produção: busca real)
            positions[platform] = {
                "rank": 5,  # Mock
                "inclusion_prob": 0.65,
                "snippet_quality": "good"
            }
        
        # Calcula métricas agregadas
        avg_rank = sum(p["rank"] for p in positions.values()) / len(positions)
        avg_inclusion = sum(p["inclusion_prob"] for p in positions.values()) / len(positions)
        
        return {
            "platforms": positions,
            "average_rank": round(avg_rank, 1),
            "inclusion_probability": round(avg_inclusion, 2),
            "visibility_score": round((100 - avg_rank * 10) * avg_inclusion, 1),
            "recommendations": self._generate_recommendations(avg_rank, avg_inclusion)
        }
    
    def _generate_recommendations(self, avg_rank: float, inclusion: float) -> List[str]:
        recs = []
        if avg_rank > 5:
            recs.append("Aumentar densidade de entidades em conteúdo técnico")
        if inclusion < 0.5:
            recs.append("Construir citações em fontes de alta autoridade (GitHub, Wikipedia)")
        if not recs:
            recs.append("Manter consistência e atualizar conteúdo trimestralmente")
        return recs