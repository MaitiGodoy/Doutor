import asyncio
import json
import logging
from typing import Dict, List, Optional
from kernel.utils import validate_json, hash_payload, load_cache, save_cache
from kernel.provider_router import ProviderRouter, ROLE_DEFAULTS
from kernel.token_policy import policy_controller
from kernel.config import TEMPERATURES, MAX_TOKENS

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
        return cache[cache_key]

    router = _get_router()
    temperature, max_tokens = _role_config(role)

    policy_controller.validate_keys_configured()
    policy_controller.log_dispatch(role, max_tokens)

    exclude_providers = []

    while True:
        try:
            provider_cfg, model_id, client = router.get_best_provider(role, exclude_names=exclude_providers)
        except Exception as e:
            raise RuntimeError(f"All providers failed or exhausted for role: {role}. Error: {e}")

        try:
            logger.info(f"Calling provider '{provider_cfg.name}' for role '{role}' using model '{model_id}'")
            
            response = await client.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            content = response.choices[0].message.content
            parsed = validate_json(content)
            
            router.mark_success(provider_cfg)
            
            tokens_used = 1000
            if hasattr(response, "usage") and response.usage:
                tokens_used = response.usage.total_tokens
                
            policy_controller.log_completion(provider_cfg.name, tokens_used, role)
            
            cache[cache_key] = parsed
            save_cache(cache)
            return parsed
            
        except Exception as e:
            logger.warning(f"Provider {provider_cfg.name} failed for role {role}: {e}")
            router.mark_failure(provider_cfg)
            exclude_providers.append(provider_cfg.name)
            await asyncio.sleep(1)
