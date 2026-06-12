import asyncio
from typing import Dict, List
import re
from collections import Counter

class GEO_ContextBuilder:
    def __init__(self):
        self.semantic_window = 150  # chars para co-ocorrência
    
    async def build(self, entities_data: Dict, target_queries: List[str]) -> Dict:
        """Constrói contexto semântico otimizado para LLMs"""
        entities = entities_data.get("entities", [])
        brand = entities_data.get("brand", "")
        
        # Calcula co-ocorrência ponderada
        cooccurrence = await self._calculate_semantic_cooccurrence(entities, target_queries)
        
        # Identifica gaps semânticos
        gaps = await self._identify_semantic_gaps(entities, target_queries)
        
        # Sugere clusters de entidades
        clusters = self._build_entity_clusters(entities)
        
        return {
            "brand": brand,
            "cooccurrence_score": cooccurrence,
            "semantic_gaps": gaps,
            "entity_clusters": clusters,
            "target_queries": target_queries,
            "recommended_density": {kw: round(100 / len(target_queries), 1) for kw in target_queries}
        }
    
    async def _calculate_semantic_cooccurrence(self, entities: List[str], queries: List[str]) -> float:
        if not entities or not queries:
            return 0.0
        
        total_score = 0.0
        max_possible = len(queries) * len(entities)
        
        for query in queries:
            for entity in entities:
                # Verifica proximidade em textos (mock - em produção usar embeddings)
                if query.lower() in entity.lower() or entity.lower() in query.lower():
                    total_score += 1.0
        
        return min(1.0, total_score / max_possible) if max_possible > 0 else 0.0
    
    async def _identify_semantic_gaps(self, entities: List[str], queries: List[str]) -> List[str]:
        gaps = []
        for query in queries:
            found = any(query.lower() in entity.lower() for entity in entities)
            if not found:
                gaps.append(f"Query '{query}' não tem entidade associada")
        return gaps
    
    def _build_entity_clusters(self, entities: List[str]) -> Dict[str, List[str]]:
        # Agrupa entidades por tipo (mock - em produção usar NER)
        clusters = {
            "people": [e for e in entities if any(word in e.lower() for word in ["dr", "prof", "fundador"])],
            "organizations": [e for e in entities if any(word in e.lower() for word in ["ltda", "inc", "sa"])],
            "locations": [e for e in entities if any(word in e.lower() for word in ["brasil", "são paulo", "rio"])],
            "methods": [e for e in entities if any(word in e.lower() for word in ["método", "protocolo", "técnica"])]
        }
        return {k: v[:10] for k, v in clusters.items() if v}