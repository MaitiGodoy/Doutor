import asyncio
from typing import Dict, List
import re
import logging

logger = logging.getLogger(__name__)

class GEO_FactCouncil:
    def __init__(self):
        self.hallucination_patterns = [
            r"provavelmente", r"talvez", r"possivelmente",
            r"deve ser", r"pode ser", r"acredita-se"
        ]
    
    async def validate(self, context: Dict) -> bool:
        """Valida factualidade e consistência do contexto"""
        issues = []
        
        # Verifica ambiguidade de entidades
        if not context.get("entity_clusters"):
            issues.append("Sem clusters de entidades definidos")
        
        # Verifica gaps semânticos críticos
        if len(context.get("semantic_gaps", [])) > 5:
            issues.append(f"Muitos gaps semânticos: {len(context['semantic_gaps'])}")
        
        # Verifica co-ocorrência mínima
        if context.get("cooccurrence_score", 0) < 0.3:
            issues.append("Co-ocorrência muito baixa (< 0.3)")
        
        if issues:
            logger.warning(f"Council rejeitou contexto: {issues}")
            return False
        
        logger.info("Council aprovou contexto")
        return True
    
    async def check_hallucination_risk(self, content: str) -> Dict:
        """Verifica risco de hallucination no conteúdo"""
        risk_score = 0.0
        
        # Verifica padrões de incerteza
        for pattern in self.hallucination_patterns:
            matches = len(re.findall(pattern, content.lower()))
            risk_score += matches * 0.1
        
        # Verifica afirmações sem fontes
        claims = len(re.findall(r"é (?:o|a|um|uma) \w+ que", content.lower()))
        sources = len(re.findall(r"(?:fonte:|segundo|conforme)", content.lower()))
        
        if claims > sources * 2:
            risk_score += 0.3
        
        return {
            "risk_score": min(1.0, risk_score),
            "risk_level": "high" if risk_score > 0.5 else "medium" if risk_score > 0.2 else "low",
            "recommendations": self._generate_fixes(risk_score)
        }
    
    def _generate_fixes(self, risk_score: float) -> List[str]:
        fixes = []
        if risk_score > 0.5:
            fixes.append("Adicionar fontes verificáveis para todas as afirmações")
            fixes.append("Remover linguagem especulativa (provavelmente, talvez)")
        if risk_score > 0.2:
            fixes.append("Incluir citações diretas de fontes primárias")
        return fixes