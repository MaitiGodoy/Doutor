import asyncio
from typing import Dict, List
import re

class GEO_HallucinationGuard:
    def __init__(self):
        self.risk_patterns = {
            "speculation": [r"provavelmente", r"talvez", r"possivelmente", r"pode ser"],
            "unverified": [r"acredita-se", r"dizem que", r"supostamente"],
            "absolute": [r"sempre", r"nunca", r"100%", r"garantido"]
        }
    
    async def audit(self, content: str) -> Dict:
        """Auditoria de qualidade e risco de hallucination"""
        risk_score = 0.0
        issues = []
        
        # Verifica padrões de risco
        for risk_type, patterns in self.risk_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, content.lower()))
                if matches > 0:
                    risk_score += matches * 0.15
                    issues.append(f"{risk_type}: {matches} ocorrências de '{pattern}'")
        
        # Verifica densidade de fontes
        source_count = len(re.findall(r"(?:fonte:|segundo|conforme|referência)", content.lower()))
        if source_count < 3:
            risk_score += 0.2
            issues.append("Poucas fontes citadas (< 3)")
        
        # Verifica afirmações absolutas sem qualificação
        absolute_claims = len(re.findall(r"é (?:o melhor|o único|o maior)", content.lower()))
        if absolute_claims > 0:
            risk_score += absolute_claims * 0.1
            issues.append(f"{absolute_claims} afirmações absolutas sem qualificação")
        
        return {
            "risk_score": min(1.0, risk_score),
            "risk_level": "high" if risk_score > 0.5 else "medium" if risk_score > 0.3 else "low",
            "issues": issues,
            "fixes": self._generate_fixes(issues),
            "passed": risk_score <= 0.3
        }
    
    def _generate_fixes(self, issues: List[str]) -> List[str]:
        fixes = []
        for issue in issues:
            if "speculation" in issue.lower():
                fixes.append("Substituir linguagem especulativa por afirmações factuais com fontes")
            if "fontes" in issue.lower():
                fixes.append("Adicionar pelo menos 3 fontes verificáveis")
            if "absolutas" in issue.lower():
                fixes.append("Qualificar afirmações absolutas com dados ou remover")
        return fixes