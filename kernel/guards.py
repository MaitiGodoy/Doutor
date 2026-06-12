import os
import re
import json
import time
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

LOG_PATH = os.getenv("SECURITY_LOG_PATH", "/var/log/security.jsonl")

# PII patterns
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,3}\)?[-.\s]?)?\d{4,5}[-.\s]?\d{4}")
CPF_RE = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
CNPJ_RE = re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b")

# Toxic keywords (pt/br + en)
TOXIC_KEYWORDS = [
    "hate", "kill", "murder", "suicide", "terror", "bomb", "violence",
    "ódio", "matar", "suicídio", "terrorismo", "bomba", "violência",
    "racismo", "nazismo", "fascismo", "pedofilia"
]

# Prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore previous", r"system prompt", r"forget rules", r"override",
    r"disregard", r"bypass", r"you are now", r"act as", r"pretend to be"
]
INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


class GuardrailCheck(BaseModel):
    """Single check result."""
    name: str
    triggered: bool
    details: Dict[str, Any] = Field(default_factory=dict)


class GuardrailResult(BaseModel):
    """Aggregated validation result."""
    status: str  # "ok" | "blocked"
    risk_score: float
    flags: List[str] = Field(default_factory=list)
    checks: List[GuardrailCheck] = Field(default_factory=list)


class SecurityGuard:
    def __init__(self):
        self.block_threshold = 0.7

    def _log_violation(self, chain_id: str, result: GuardrailResult, text: str):
        entry = {
            "timestamp": time.time(),
            "chain_id": chain_id,
            "status": result.status,
            "risk_score": result.risk_score,
            "flags": result.flags,
            "text_snippet": text[:200],
        }
        try:
            os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass  # best effort

    def calculate_risk(self, text: str) -> float:
        """Heuristic risk 0.0-1.0."""
        score = 0.0
        # PII
        if EMAIL_RE.search(text) or PHONE_RE.search(text) or CPF_RE.search(text) or CNPJ_RE.search(text):
            score += 0.3
        # Toxic
        toxic_hits = sum(1 for kw in TOXIC_KEYWORDS if kw.lower() in text.lower())
        if toxic_hits:
            score += min(0.4, toxic_hits * 0.1)
        # Injection
        if INJECTION_RE.search(text):
            score += 0.5
        return min(1.0, score)

    def _run_checks(self, text: str, context: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        checks = []
        flags = []

        # PII check
        pii = bool(EMAIL_RE.search(text) or PHONE_RE.search(text) or CPF_RE.search(text) or CNPJ_RE.search(text))
        checks.append(GuardrailCheck(name="pii", triggered=pii, details={"patterns": ["email","phone","cpf","cnpj"]}))
        if pii:
            flags.append("pii")

        # Toxic check
        toxic_hits = [kw for kw in TOXIC_KEYWORDS if kw.lower() in text.lower()]
        toxic = bool(toxic_hits)
        checks.append(GuardrailCheck(name="toxicity", triggered=toxic, details={"keywords": toxic_hits}))
        if toxic:
            flags.append("toxicity")

        # Injection check
        injection = bool(INJECTION_RE.search(text))
        checks.append(GuardrailCheck(name="prompt_injection", triggered=injection, details={}))
        if injection:
            flags.append("prompt_injection")

        risk = self.calculate_risk(text)
        status = "blocked" if risk >= self.block_threshold else "ok"
        return GuardrailResult(status=status, risk_score=round(risk, 3), flags=flags, checks=checks)

    def validate_input(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        result = self._run_checks(prompt, context)
        if result.status == "blocked":
            chain_id = context.get("chain_id") if context else "unknown"
            self._log_violation(chain_id, result, prompt)
        return result

    def validate_output(self, content: str, context: Optional[Dict[str, Any]] = None) -> GuardrailResult:
        result = self._run_checks(content, context)
        if result.status == "blocked":
            chain_id = context.get("chain_id") if context else "unknown"
            self._log_violation(chain_id, result, content)
        return result

    def allow(self, tool: str, args: Dict[str, Any]) -> bool:
        """Simple policy: allow all tools for now."""
        # Could add tool-specific rules here.
        return True


# Compatibility exports expected by __init__.py
def get_guardrails() -> SecurityGuard:
    return SecurityGuard()


class NVIDIA_Guardrails(SecurityGuard):
    """Alias for NVIDIA-specific guardrails (currently same logic)."""
    pass


# Re-export models
__all__ = [
    "SecurityGuard",
    "get_guardrails",
    "NVIDIA_Guardrails",
    "GuardrailCheck",
    "GuardrailResult",
]
