"""
Council Agent — Doutor v5.0
Validação ética, compliance, governança e auditoria de decisões.
Conselho de ética automatizado para garantir que todas as ações
estejam dentro das políticas e regulamentos.
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from kernel.llm_client import call_llm

logger = logging.getLogger("doutor.council")

ETHICS_SYSTEM_PROMPT = """You are an ethics and compliance auditor for an AI system.
Analyze the given action/decision against ethical guidelines and compliance policies.
Return valid JSON with: 
- ethical_status (approved/flagged/rejected)
- risk_level (low/medium/high/critical)
- violations (array of {policy, severity, description} if any)
- warnings (array of strings)
- recommended_mitigations (array of strings)
- final_verdict (string explanation)
Be strict but fair. Use Brazilian data protection laws (LGPD) and ethical AI principles."""

COMPLIANCE_SYSTEM_PROMPT = """You are a senior compliance officer specializing in Brazilian regulations.
Audit the given content/code/decision against:
1. LGPD (Lei Geral de Proteção de Dados)
2. Marco Civil da Internet
3. Código de Defesa do Consumidor
4. Ethical AI guidelines
5. Platform-specific policies

Return valid JSON with:
- compliance_status (pass/fail/needs_review)
- regulation_checks (array of {regulation, status, notes})
- critical_issues (array of strings)
- recommendations (array of strings)
- overall_score (0-100)
"""

GOVERNANCE_SYSTEM_PROMPT = """You are a governance auditor for AI-driven business operations.
Review the proposed action against governance policies.
Return valid JSON with:
- governance_status (approved/flagged/rejected)
- policy_checks (array of {policy, status, details})
- risks_identified (array of strings)
- required_approvals (array of strings)
- audit_trail_suggestions (array of strings)
- final_recommendation (string)
"""


class CouncilAgent:
    """Agente de Conselho — auditoria ética, compliance e governança"""

    def __init__(self):
        self.audit_log = []

    async def ethics_check(self, action_description: str, context: str = "") -> Dict:
        """Valida se uma ação é ética antes de executar"""
        user_prompt = f"""
Action to validate: {action_description}
Context: {context or "No additional context"}
Timestamp: {datetime.now().isoformat()}

Perform a thorough ethics audit of this action. Consider:
- Is it deceptive or misleading?
- Does it respect user privacy and data rights?
- Is it transparent about its nature?
- Does it comply with LGPD?
- Could it cause harm?
"""
        try:
            result = await call_llm("the_constitution", ETHICS_SYSTEM_PROMPT, user_prompt)
            result["action"] = action_description
            result["reviewed_at"] = datetime.now().isoformat()

            # Log the audit
            self.audit_log.append({
                "timestamp": result["reviewed_at"],
                "action": action_description,
                "status": result.get("ethical_status", "unknown"),
                "risk_level": result.get("risk_level", "unknown")
            })

            logger.info(f"Ethics check: {result.get('ethical_status', 'unknown')} for '{action_description[:60]}'")
            return {"status": "ok", "data": result}
        except Exception as e:
            logger.error(f"Ethics check failed: {e}")
            return {"status": "error", "error": str(e), "action": action_description}

    async def compliance_audit(self, target: str, audit_type: str = "content", content: str = "") -> Dict:
        """Auditoria de compliance contra regulamentações brasileiras"""
        user_prompt = f"""
Audit Target: {target}
Audit Type: {audit_type}
Content to audit: {content[:3000] if content else "No content provided"}
Date: {datetime.now().strftime("%Y-%m-%d")}

Perform a full compliance audit against Brazilian regulations (LGPD, Marco Civil, CDC).
"""
        try:
            system = COMPLIANCE_SYSTEM_PROMPT if audit_type == "content" else GOVERNANCE_SYSTEM_PROMPT
            result = await call_llm("the_inspector", system, user_prompt)
            result["target"] = target
            result["audit_type"] = audit_type
            result["audited_at"] = datetime.now().isoformat()

            self.audit_log.append({
                "timestamp": result["audited_at"],
                "target": target,
                "status": result.get("compliance_status", result.get("governance_status", "unknown"))
            })

            logger.info(f"Compliance audit: {result.get('compliance_status', 'completed')} for '{target[:60]}'")
            return {"status": "ok", "data": result}
        except Exception as e:
            logger.error(f"Compliance audit failed: {e}")
            return {"status": "error", "error": str(e), "target": target}

    async def governance_validation(self, proposal: str, department: str = "general") -> Dict:
        """Valida proposta contra políticas de governança"""
        user_prompt = f"""
Proposal: {proposal}
Department: {department}
Timestamp: {datetime.now().isoformat()}

Validate this proposal against governance policies and provide an audit trail.
"""
        try:
            result = await call_llm("the_constitution", GOVERNANCE_SYSTEM_PROMPT, user_prompt)
            result["proposal"] = proposal
            result["department"] = department
            result["validated_at"] = datetime.now().isoformat()

            logger.info(f"Governance validation: {result.get('governance_status', 'completed')}")
            return {"status": "ok", "data": result}
        except Exception as e:
            logger.error(f"Governance validation failed: {e}")
            return {"status": "error", "error": str(e), "proposal": proposal}

    def get_audit_history(self, limit: int = 20) -> Dict:
        """Retorna histórico de auditorias realizadas"""
        return {
            "status": "ok",
            "total_audits": len(self.audit_log),
            "recent_audits": self.audit_log[-limit:]
        }
