import asyncio
import json
import logging
from typing import Dict, List, Optional

from kernel.utils import validate_json, hash_payload, load_cache, save_cache
from kernel.provider_router import ProviderRouter, ROLE_DEFAULTS
from kernel.token_policy import policy_controller
from kernel.config import TEMPERATURES, MAX_TOKENS, PRODUCTION
from kernel.provider_quotas import circuit_breaker_status, get_healthy_providers
from kernel.state_store import log_audit

logger = logging.getLogger("antimatter.client")

_router: Optional[ProviderRouter] = None

def _get_router() -> ProviderRouter:
    global _router
    if _router is None:
        _router = ProviderRouter()
    return _router

def _role_config(role: str) -> tuple:
    temp = TEMPERATURES.get(role)
    maxt = MAX_TOKENS.get(role)
    if temp is None and role in ROLE_DEFAULTS:
        temp = ROLE_DEFAULTS[role].temperature
        maxt = ROLE_DEFAULTS[role].max_tokens
    return temp or 0.3, maxt or 2048

async def call_llm(role: str, system: str, user: str) -> Dict:
    cache_key = hash_payload({"role": role, "system": system, "user": user})
    cache = load_cache()
    if cache_key in cache:
        log_audit(role, "cache_hit", cache_key, cache_key, "ok")
        return cache[cache_key]

    router = _get_router()
    temperature, max_tokens = _role_config(role)

    # Circuit breaker check — if all providers blocked, use cache-only mode
    circuit = circuit_breaker_status()
    if circuit.get("all_blocked"):
        if cache_key in cache:
            log_audit(role, "circuit_breaker_cache", cache_key, cache_key, "ok")
            return cache[cache_key]
        from kernel.config import PRODUCTION
        log_audit(role, "circuit_breaker_blocked", cache_key, "", "blocked")
        raise RuntimeError(
            f"LOW POWER MODE: All providers blocked (daily quota exhausted). "
            f"Request for role='{role}' cannot be served. "
            f"Try again after midnight UTC or configure a low-power fallback model."
        )

    exclude_providers = []

    while True:
        if all(p.name in exclude_providers for p in router.providers):
            circuit = circuit_breaker_status()
            if circuit.get("all_blocked"):
                raise RuntimeError(
                    f"Low-power mode: all providers exhausted. "
                    f"Try again after midnight UTC reset."
                )
            raise RuntimeError(f"All providers failed for role: {role}")

        try:
            provider_cfg, model_id, client = router.get_best_provider(role, exclude_names=exclude_providers)
            # Adquire slot de concorrência (não-bloqueante; se lotado, router pula)

            # (O acquire é tentado no router.get_provider_for_agent internamente)
        except Exception as e:
            raise RuntimeError(f"All providers failed for role: {role}. Error: {e}")

        # Marca slot como ocupado
        slot_acquired = False
        if provider_cfg.max_concurrent > 0:
            slot_acquired = router.acquire_concurrent_slot(provider_cfg.name)

        try:
            logger.info(f"Calling {provider_cfg.name} for role {role} model {model_id}")

            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=120,  # Timeout global para evitar hangs
            )

            content = response.choices[0].message.content
            parsed = validate_json(content)

            router.mark_success(provider_cfg)

            tokens_used = 1000
            if hasattr(response, "usage") and response.usage:
                tokens_used = response.usage.total_tokens

            policy_controller.log_completion(provider_cfg.name, tokens_used, role)
            log_audit(role, "llm_call", cache_key, hash_payload(parsed), "ok", {
                "provider": provider_cfg.name,
                "model": model_id,
                "tokens": tokens_used,
            })

            cache[cache_key] = parsed
            save_cache(cache)
            return parsed

        except Exception as e:
            logger.warning(f"Provider {provider_cfg.name} failed for role {role}: {e}")
            router.mark_failure(provider_cfg)
            exclude_providers.append(provider_cfg.name)
            await asyncio.sleep(1)
        finally:
            if slot_acquired:
                router.release_concurrent_slot(provider_cfg.name)
