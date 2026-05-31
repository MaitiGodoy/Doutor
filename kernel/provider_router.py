"""
Antimatter Squad — Provider Router + Model Registry
Multi-provider (OpenRouter / Groq / HuggingFace) with health check,
automatic fallback, and budget-aware routing.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI

logger = logging.getLogger("antimatter.router")


# ═══════════════════════════════════════════════════════
# Model Configuration per Role
# ═══════════════════════════════════════════════════════

@dataclass
class RoleConfig:
    temperature: float
    max_tokens: int


ROLE_DEFAULTS: Dict[str, RoleConfig] = {
    "planner_a":  RoleConfig(temperature=0.6, max_tokens=3072),
    "planner_b":  RoleConfig(temperature=0.7, max_tokens=3072),
    "coder":      RoleConfig(temperature=0.2, max_tokens=4096),
    "programmer": RoleConfig(temperature=0.2, max_tokens=4096),
    "creator":    RoleConfig(temperature=0.3, max_tokens=4096),
    "auditor":    RoleConfig(temperature=0.3, max_tokens=4096),
    "reviewer_e": RoleConfig(temperature=0.5, max_tokens=3072),
    "reviewer_f": RoleConfig(temperature=0.5, max_tokens=3072),
    "tester":     RoleConfig(temperature=0.4, max_tokens=3072),
    "corrector":  RoleConfig(temperature=0.2, max_tokens=4096),
    "optimizer":  RoleConfig(temperature=0.4, max_tokens=3072),
    "strategist_a": RoleConfig(temperature=0.6, max_tokens=3072),
    "strategist_b": RoleConfig(temperature=0.7, max_tokens=3072),
    "producer":   RoleConfig(temperature=0.3, max_tokens=4096),
    "halbert":    RoleConfig(temperature=0.9, max_tokens=3072),
    "ogilvy":     RoleConfig(temperature=0.7, max_tokens=3072),
    "kennedy":    RoleConfig(temperature=0.8, max_tokens=3072),
    "concierge":  RoleConfig(temperature=0.5, max_tokens=2048),
}


# ═══════════════════════════════════════════════════════
# Provider Configurations
# ═══════════════════════════════════════════════════════

@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    models: Dict[str, str]
    priority: int
    healthy: bool = True
    last_check: float = 0.0
    consecutive_failures: int = 0
    daily_request_count: int = 0
    daily_request_limit: int = 200
    extra_headers: Dict[str, str] = field(default_factory=dict)


def load_providers() -> List[ProviderConfig]:
    """Load provider configs from environment variables."""
    providers = []

    # 1. OpenRouter (primary) — models verified against /api/v1/models free tier
    or_key = os.getenv("OPENROUTER_API_KEY", "")
    if or_key:
        providers.append(ProviderConfig(
            name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key=or_key,
            priority=1,
            daily_request_limit=200,
            models={
                "planner_a":    "meta-llama/llama-3.3-70b-instruct:free",
                "planner_b":    "google/gemma-2-9b-it:free",
                "coder":        "qwen/qwen-2.5-coder-32b-instruct:free",
                "programmer":   "qwen/qwen-2.5-coder-32b-instruct:free",
                "creator":      "qwen/qwen-2.5-7b-instruct:free",
                "auditor":      "qwen/qwen-2.5-coder-32b-instruct:free",
                "reviewer_e":   "meta-llama/llama-3.2-3b-instruct:free",
                "reviewer_f":   "meta-llama/llama-3.2-3b-instruct:free",
                "tester":       "meta-llama/llama-3.2-3b-instruct:free",
                "corrector":    "qwen/qwen-2.5-coder-32b-instruct:free",
                "optimizer":    "qwen/qwen-2.5-coder-32b-instruct:free",
                "strategist_a": "meta-llama/llama-3.3-70b-instruct:free",
                "strategist_b": "google/gemma-2-9b-it:free",
                "producer":     "qwen/qwen-2.5-7b-instruct:free",
                "halbert":      "google/gemma-2-9b-it:free",
                "ogilvy":       "google/gemma-2-9b-it:free",
                "kennedy":      "google/gemma-2-9b-it:free",
                "concierge":    "qwen/qwen-2.5-7b-instruct:free",
            },
            extra_headers={
                "HTTP-Referer": "https://github.com/antimatter-squad",
                "X-Title": "Antimatter Squad Orchestrator",
            },
        ))

    # 2. Groq (fallback 1)
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        providers.append(ProviderConfig(
            name="groq",
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key,
            priority=2,
            daily_request_limit=500,
            models={
                "planner_a":    "llama-3.1-8b-instant",
                "planner_b":    "llama-3.3-70b-versatile",
                "coder":        "qwen-qwq-32b",
                "programmer":   "qwen-qwq-32b",
                "creator":      "llama-3.1-8b-instant",
                "auditor":      "qwen-qwq-32b",
                "reviewer_e":   "llama-3.1-8b-instant",
                "reviewer_f":   "llama-3.3-70b-versatile",
                "tester":       "llama-3.1-8b-instant",
                "corrector":    "qwen-qwq-32b",
                "optimizer":    "llama-3.1-8b-instant",
                "strategist_a": "llama-3.3-70b-versatile",
                "strategist_b": "llama-3.1-8b-instant",
                "producer":     "llama-3.1-8b-instant",
                "halbert":      "llama-3.1-8b-instant",
                "ogilvy":       "llama-3.1-8b-instant",
                "kennedy":      "llama-3.1-8b-instant",
                "concierge":    "llama-3.1-8b-instant",
            },
        ))

    # 3. HuggingFace (fallback 2)
    hf_key = os.getenv("HUGGINGFACE_API_KEY", "")
    if hf_key:
        providers.append(ProviderConfig(
            name="huggingface",
            base_url="https://router.huggingface.co/v1",
            api_key=hf_key,
            priority=3,
            daily_request_limit=300,
            models={
                "planner_a":    "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "planner_b":    "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "coder":        "Qwen/Qwen2.5-Coder-32B-Instruct",
                "programmer":   "Qwen/Qwen2.5-Coder-32B-Instruct",
                "creator":      "Qwen/Qwen2.5-Coder-32B-Instruct",
                "auditor":      "Qwen/Qwen2.5-Coder-32B-Instruct",
                "reviewer_e":   "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "reviewer_f":   "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "tester":       "Qwen/Qwen2.5-Coder-32B-Instruct",
                "corrector":    "Qwen/Qwen2.5-Coder-32B-Instruct",
                "optimizer":    "Qwen/Qwen2.5-Coder-32B-Instruct",
                "strategist_a": "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "strategist_b": "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "producer":     "Qwen/Qwen2.5-Coder-32B-Instruct",
                "halbert":      "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "ogilvy":       "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "kennedy":      "meta-llama/Meta-Llama-3.1-8B-Instruct",
                "concierge":    "meta-llama/Meta-Llama-3.1-8B-Instruct",
            },
        ))

    providers.sort(key=lambda p: p.priority)
    return providers


class ProviderRouter:
    """
    Routes agent calls to the best available provider.
    Tracks health, budget, rate limits, and auto-fallback.
    """

    def __init__(self, providers: Optional[List[ProviderConfig]] = None):
        self.providers = providers or load_providers()
        self._clients: Dict[str, AsyncOpenAI] = {}
        self._health_cache_ttl = 60  # seconds

        if not self.providers:
            raise RuntimeError(
                "No AI providers configured. Set at least OPENROUTER_API_KEY "
                "in environment variables."
            )

        logger.info(
            f"ProviderRouter initialized with {len(self.providers)} providers: "
            f"{[p.name for p in self.providers]}"
        )

    def _get_client(self, provider: ProviderConfig) -> AsyncOpenAI:
        """Get or create an AsyncOpenAI client for a provider."""
        if provider.name not in self._clients:
            self._clients[provider.name] = AsyncOpenAI(
                api_key=provider.api_key,
                base_url=provider.base_url,
                max_retries=0,  # We handle retries ourselves
                default_headers=provider.extra_headers or None,
            )
        return self._clients[provider.name]

    async def health_check(self, provider: ProviderConfig) -> bool:
        """
        Lightweight health check — tries a minimal API call.
        Caches result for _health_cache_ttl seconds.
        """
        now = time.time()
        if now - provider.last_check < self._health_cache_ttl:
            return provider.healthy

        try:
            client = self._get_client(provider)
            # Minimal completion call to test connectivity
            first_model = list(provider.models.values())[0]
            resp = await asyncio.wait_for(
                client.chat.completions.create(
                    model=first_model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=5,
                    temperature=0,
                ),
                timeout=15,
            )
            provider.healthy = True
            provider.consecutive_failures = 0
            logger.info(f"Health check PASS: {provider.name}")
        except Exception as e:
            error_str = str(e).lower()
            # 429 = rate limited but reachable — still healthy
            if "429" in error_str or "rate" in error_str:
                provider.healthy = True
                provider.consecutive_failures = 0
                logger.info(f"Health check PASS (rate-limited): {provider.name}")
            else:
                provider.healthy = False
                provider.consecutive_failures += 1
                logger.warning(f"Health check FAIL: {provider.name}: {e}")

        provider.last_check = now
        return provider.healthy

    async def health_check_all(self) -> Dict[str, bool]:
        """Run health checks on all providers in parallel."""
        results = {}
        tasks = []
        for p in self.providers:
            tasks.append(self.health_check(p))

        checks = await asyncio.gather(*tasks, return_exceptions=True)
        for p, result in zip(self.providers, checks):
            results[p.name] = result if isinstance(result, bool) else False
        return results

    def get_best_provider(
        self, role: str, exclude_names: Optional[List[str]] = None
    ) -> Tuple[ProviderConfig, str, AsyncOpenAI]:
        """
        Returns (provider, model_id, client) for the given role.
        Falls back through providers sorted by priority, skipping unhealthy ones or excluded ones.
        """
        exclude = exclude_names or []
        for provider in self.providers:
            if provider.name in exclude:
                continue
            if not provider.healthy:
                # Auto-recover unhealthy providers after 30 seconds to handle temporary rate limits
                if time.time() - provider.last_check > 30:
                    provider.healthy = True
                    provider.consecutive_failures = 0
                    logger.info(f"Provider {provider.name} auto-recovered from UNHEALTHY state")
                else:
                    continue
            if provider.daily_request_count >= provider.daily_request_limit:
                logger.warning(
                    f"Provider {provider.name} at daily limit "
                    f"({provider.daily_request_count}/{provider.daily_request_limit})"
                )
                continue
            model_id = provider.models.get(role)
            if model_id:
                client = self._get_client(provider)
                return provider, model_id, client

        # All providers exhausted — force first provider that is not excluded
        available = [p for p in self.providers if p.name not in exclude]
        p = available[0] if available else self.providers[0]
        model_id = p.models.get(role, list(p.models.values())[0])
        logger.error(f"All providers exhausted for role={role}, forcing {p.name}/{model_id}")
        return p, model_id, self._get_client(p)

    def mark_failure(self, provider: ProviderConfig) -> None:
        """Mark a provider as having a failure (for rate limit or error)."""
        provider.consecutive_failures += 1
        provider.last_check = time.time()
        if provider.consecutive_failures >= 3:
            provider.healthy = False
            logger.warning(
                f"Provider {provider.name} marked UNHEALTHY after "
                f"{provider.consecutive_failures} consecutive failures"
            )

    def mark_success(self, provider: ProviderConfig) -> None:
        """Mark a successful call."""
        provider.consecutive_failures = 0
        provider.daily_request_count += 1

    def budget_status(self) -> Dict[str, Any]:
        """Returns budget/usage status for all providers."""
        return {
            p.name: {
                "healthy": p.healthy,
                "requests_used": p.daily_request_count,
                "requests_limit": p.daily_request_limit,
                "pct_used": round(
                    p.daily_request_count / max(1, p.daily_request_limit) * 100, 1
                ),
                "consecutive_failures": p.consecutive_failures,
            }
            for p in self.providers
        }

    def reset_daily_counts(self) -> None:
        """Reset daily counters (call at midnight or start of new pipeline batch)."""
        for p in self.providers:
            p.daily_request_count = 0
            p.healthy = True
            p.consecutive_failures = 0
