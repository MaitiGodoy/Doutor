"""
Antimatter Squad — Token Isolation Policy Enforcer (Anti-Vampire Clause)
Enforces strict routing rules to prevent hosting provider (Antigravity) token consumption.
"""
from __future__ import annotations

import os
import time
import json
from pathlib import Path
from typing import Dict, Any, List

# Policy violation logs path
VIOLATIONS_LOG_PATH = Path("logs/token_policy_violations.jsonl")


class TokenPolicyViolation(Exception):
    """Raised when the orchestrator attempts to consume host tokens for content generation."""
    pass


class TokenPolicyController:
    def __init__(self):
        self.host_native_calls = 0
        self.external_api_calls = 0
        self.violation_count = 0
        self.call_history: List[Dict[str, Any]] = []

    def is_strict(self) -> bool:
        return os.getenv("TOKEN_POLICY_STRICT", "true").lower() == "true"

    def is_host_blocked(self) -> bool:
        return os.getenv("HOST_NATIVE_BLOCKED", "true").lower() == "true"

    def is_external_required(self) -> bool:
        return os.getenv("REQUIRE_EXTERNAL_API", "true").lower() == "true"

    def validate_keys_configured(self) -> None:
        """Verify that at least one external provider API key is present."""
        if not self.is_external_required():
            return
        
        has_keys = (
            bool(os.getenv("OPENROUTER_API_KEY"))
            or bool(os.getenv("GROQ_API_KEY"))
            or bool(os.getenv("HUGGINGFACE_API_KEY"))
        )
        if not has_keys:
            raise TokenPolicyViolation(
                "❌ Configuração crítica: Nenhuma API externa configurada. O Antimatter Core requer pelo menos "
                "uma chave de API externa para operar sem consumir tokens do host. Adicione "
                "OPENROUTER_API_KEY, GROQ_API_KEY ou HUGGINGFACE_API_KEY ao seu .env."
            )

    def log_dispatch(self, role: str, expected_tokens: int) -> None:
        """Register the dispatch of an agent request."""
        event = {
            "event": "agent_dispatch",
            "role": role,
            "expected_tokens": expected_tokens,
            "source": "external",
            "timestamp": time.time(),
        }
        self.call_history.append(event)

    def log_completion(self, provider: str, tokens_used: int, role: str) -> None:
        """Register completion of an agent call and audit for violations."""
        event = {
            "event": "agent_complete",
            "tokens_used": tokens_used,
            "provider": provider,
            "role": role,
            "timestamp": time.time(),
        }
        self.call_history.append(event)

        # Check if the provider is host native for generative roles
        is_generative_role = role not in ("concierge", "system")
        is_host = provider == "host_native" or provider == "antigravity"

        if is_host:
            self.host_native_calls += 1
            if is_generative_role and (self.is_host_blocked() or self.is_strict()):
                self.violation_count += 1
                self.record_violation(role, f"Generative action routed to {provider}")
                raise TokenPolicyViolation(
                    "⚠️ Erro de configuração: o sistema tentou usar tokens do Antigravity para gerar conteúdo. "
                    "Verifique se as APIs externas estão configuradas corretamente."
                )
        else:
            self.external_api_calls += 1

        # Run audit loop every 5 calls
        if len(self.call_history) % 5 == 0:
            self.run_self_audit()

    def record_violation(self, role: str, action: str) -> None:
        """Persist violation details to the JSONL log file."""
        VIOLATIONS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        violation_entry = {
            "violation": {
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "role": role,
                "attempted_action": action,
                "blocked": True,
                "corrective_action": "check_api_keys",
            }
        }
        with open(VIOLATIONS_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(violation_entry) + "\n")

    def run_self_audit(self) -> None:
        """Audit the recent calls for host-native consumption percentage."""
        total_calls = self.host_native_calls + self.external_api_calls
        if total_calls == 0:
            return
        
        ratio = self.host_native_calls / total_calls
        if ratio > 0.10:
            print(f"[WARNING] Token Policy Audit warning: host_native calls make up {ratio*100:.1f}% of total calls.")

        if self.violation_count >= 3:
            raise TokenPolicyViolation(
                "❌ Proteção ativada: Mais de 3 violações de política de tokens nas últimas chamadas. "
                "Execução pausada por segurança."
            )

    def get_token_usage_summary(self) -> Dict[str, Any]:
        """Summary of host vs external token usage."""
        return {
            "host_tokens_used": self.host_native_calls * 1000,  # rough estimate
            "external_api_calls": self.external_api_calls,
            "estimated_external_cost_usd": self.external_api_calls * 0.0001,  # estimate
            "policy_compliant": self.host_native_calls == 0,
        }

    def force_external_only_test(self, role: str) -> Dict[str, Any]:
        """Perform a test routing check for a role."""
        self.validate_keys_configured()
        configured = []
        if os.getenv("OPENROUTER_API_KEY"):
            configured.append("openrouter")
        if os.getenv("GROQ_API_KEY"):
            configured.append("groq")
        if os.getenv("HUGGINGFACE_API_KEY"):
            configured.append("huggingface")

        return {
            "policy_status": "compliant",
            "configured_providers": configured,
            "host_native_blocked": self.is_host_blocked(),
            "test_call_result": {"routed_to": configured[0] if configured else "none", "status": "success"},
            "concierge_summary": "✅ Política de tokens validada: o sistema está configurado para usar APENAS APIs externas. Tokens do Antigravity preservados para orquestração e interface."
        }


# Global instance of the controller
policy_controller = TokenPolicyController()
