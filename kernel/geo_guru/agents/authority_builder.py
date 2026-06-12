import asyncio
from typing import Dict, List

class GEO_AuthorityBuilder:
    def __init__(self):
        self.authority_sources = {
            "tier1": ["Wikipedia", "GitHub", "arXiv", "Google Scholar"],
            "tier2": ["Medium", "Dev.to", "Crunchbase", "LinkedIn"],
            "tier3": ["Reddit", "Quora", "Stack Overflow", "Product Hunt"]
        }
    
    async def build_strategy(self, brand: str, entities: List[str]) -> Dict:
        """Estratégia de construção de autoridade em fontes que IAs consomem"""
        strategy = {
            "tier1_actions": await self._generate_tier1_actions(brand, entities),
            "tier2_actions": await self._generate_tier2_actions(brand),
            "timeline": "3-6 meses para impacto significativo",
            "expected_authority_gain": "30-50 pontos no GEO Authority Score"
        }
        return strategy
    
    async def _generate_tier1_actions(self, brand: str, entities: List[str]) -> List[Dict]:
        return [
            {"platform": "GitHub", "action": "Criar repositório open-source com documentação técnica", "impact": "high"},
            {"platform": "Wikipedia", "action": "Verificar notabilidade e sugerir artigo", "impact": "high"},
            {"platform": "arXiv", "action": "Publicar paper técnico (se aplicável)", "impact": "medium"},
            {"platform": "Google Scholar", "action": "Indexar publicações acadêmicas", "impact": "medium"}
        ]
    
    async def _generate_tier2_actions(self, brand: str) -> List[Dict]:
        return [
            {"platform": "Medium", "action": "Publicar série de artigos técnicos", "impact": "medium"},
            {"platform": "Crunchbase", "action": "Cadastrar perfil da empresa/projeto", "impact": "low"},
            {"platform": "LinkedIn", "action": "Otimizar página da empresa", "impact": "low"}
        ]