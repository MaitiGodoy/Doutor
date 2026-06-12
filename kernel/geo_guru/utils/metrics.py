from typing import Dict, List
from dataclasses import dataclass

@dataclass
class GEOMetrics:
    def calculate_authority_score(self, analysis: Dict, comp_analysis: Dict, serp_positions: Dict) -> float:
        # Peso: 40% entidade, 30% citações, 30% SERP
        entity_score = analysis.get("cooccurrence_score", 0) * 100
        citation_score = min(analysis.get("citation_estimate", 0) / 50 * 100, 100)
        serp_score = sum(100 - pos for pos in serp_positions.values()) / max(len(serp_positions), 1)
        
        return (entity_score * 0.4) + (citation_score * 0.3) + (serp_score * 0.3)
    
    def calculate_visibility_index(self, serp_positions: Dict, citations: List) -> float:
        if not serp_positions:
            return 0.0
        avg_position = sum(serp_positions.values()) / len(serp_positions)
        citation_boost = min(len(citations) * 5, 50)
        return max(0, min(100, (100 - avg_position * 10) + citation_boost))
    
    def estimate_impact(self, priorities: List[Dict], authority_score: float) -> float:
        if not priorities:
            return 0.0
        avg_roi = sum(p["roi_score"] for p in priorities) / len(priorities)
        return min(100, (authority_score * 0.5) + (avg_roi * 50))