import time
import logging
from typing import Dict, Optional
from datetime import datetime, timezone
from kernel.state_store import get_provider_quota, upsert_provider_quota, get_all_provider_quotas, reset_daily_quotas

logger = logging.getLogger("antimatter.quotas")

DAILY_LIMITS = {
    "openrouter": 200,
    "groq": 500,
    "huggingface": 100,
    "fireworks": 150,
    "together": 100,
}


def _utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _check_midnight_reset(quota: Dict) -> Dict:
    today = _utc_date()
    if quota.get("last_reset_utc") != today:
        quota["used_today"] = 0
        quota["is_blocked"] = 0
        quota["last_reset_utc"] = today
        upsert_provider_quota(
            provider=quota["provider"],
            used_today=0,
            daily_limit=quota.get("daily_limit", DAILY_LIMITS.get(quota["provider"], 200)),
            last_reset_utc=today,
            is_blocked=0,
        )
    return quota


def ensure_provider_quota(provider: str) -> Dict:
    daily_limit = DAILY_LIMITS.get(provider, 200)
    quota = get_provider_quota(provider)
    if quota.get("daily_limit") is None:
        upsert_provider_quota(provider, 0, daily_limit, _utc_date(), 0)
        quota = get_provider_quota(provider)
    return _check_midnight_reset(quota)


def check_quota(provider: str) -> Dict:
    quota = ensure_provider_quota(provider)
    if quota["is_blocked"]:
        return {"allowed": False, "reason": f"Provider {provider} is BLOCKED", "used": quota["used_today"], "daily_limit": quota["daily_limit"]}
    if quota["used_today"] >= quota["daily_limit"]:
        return {"allowed": False, "reason": f"Daily limit reached ({quota['used_today']}/{quota['daily_limit']})", "used": quota["used_today"], "daily_limit": quota["daily_limit"]}
    return {"allowed": True, "reason": "OK", "used": quota["used_today"], "daily_limit": quota["daily_limit"]}


def increment_quota(provider: str) -> Dict:
    quota = ensure_provider_quota(provider)
    new_used = quota["used_today"] + 1
    is_blocked = 1 if new_used >= quota["daily_limit"] else 0
    upsert_provider_quota(provider, new_used, quota["daily_limit"], _utc_date(), is_blocked)
    return {"provider": provider, "used_today": new_used, "daily_limit": quota["daily_limit"], "is_blocked": bool(is_blocked)}


def block_provider(provider: str):
    quota = ensure_provider_quota(provider)
    upsert_provider_quota(provider, quota["used_today"], quota["daily_limit"], _utc_date(), 1)


def get_all_quotas() -> list:
    quotas = get_all_provider_quotas()
    today = _utc_date()
    for q in quotas:
        if q.get("last_reset_utc") != today:
            q["used_today"] = 0
            q["is_blocked"] = 0
            q["last_reset_utc"] = today
            upsert_provider_quota(q["provider"], 0, q.get("daily_limit", 200), today, 0)
    return get_all_provider_quotas()


def get_healthy_providers() -> list:
    quotas = get_all_quotas()
    return [q for q in quotas if not q["is_blocked"] and q["used_today"] < q["daily_limit"]]


def get_next_available(start_from: Optional[str] = None) -> Optional[str]:
    healthy = get_healthy_providers()
    if not healthy:
        return None
    if start_from:
        for i, q in enumerate(healthy):
            if q["provider"] == start_from and i + 1 < len(healthy):
                return healthy[i + 1]["provider"]
        return healthy[0]["provider"]
    return healthy[0]["provider"]


def circuit_breaker_status() -> Dict:
    healthy = get_healthy_providers()
    all_quotas = get_all_quotas()
    total_providers = len(all_quotas)
    return {
        "healthy_count": len(healthy),
        "total_providers": total_providers,
        "all_blocked": len(healthy) == 0,
        "providers": [
            {
                "provider": q["provider"],
                "used": q["used_today"],
                "daily_limit": q["daily_limit"],
                "blocked": bool(q["is_blocked"]),
                "pct": round(q["used_today"] / max(1, q["daily_limit"]) * 100, 1),
            }
            for q in all_quotas
        ],
    }
