import os
import json
import time
import asyncio
from enum import Enum
from typing import Dict, Any, Optional
import httpx
from dataclasses import dataclass

@dataclass
class RoleDefaults:
    temperature: float
    max_tokens: int

ROLE_DEFAULTS = {
    "default": RoleDefaults(0.3, 2048),
    "creative": RoleDefaults(0.7, 4096),
    "analytical": RoleDefaults(0.2, 4096),
}

METRICS_PATH = os.getenv("PROVIDER_METRICS_PATH", "/var/log/provider_metrics.jsonl")

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, name: str, failure_threshold: int = 3, reset_timeout: int = 60):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

    def record_success(self):
        self.failures = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def can_attempt(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            if self.last_failure_time and (time.time() - self.last_failure_time) >= self.reset_timeout:
                self.state = CircuitState.HALF_OPEN
                return True
            return False
        # HALF_OPEN allows one attempt
        return True

class ProviderRouter:
    def __init__(self):
        self.providers = [
            {
                "name": "nvidia",
                "base_url": os.getenv("NVIDIA_API_BASE", "https://api.nvidia.com/v1"),
                "api_key_env": "NVIDIA_API_KEY",
                "model": os.getenv("NVIDIA_MODEL", "nemotron-3-ultra"),
            },
            {
                "name": "openrouter",
                "base_url": os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1"),
                "api_key_env": "OPENROUTER_API_KEY",
                "model": os.getenv("OPENROUTER_MODEL", "openrouter/auto"),
            },
            {
                "name": "groq",
                "base_url": os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1"),
                "api_key_env": "GROQ_API_KEY",
                "model": os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"),
            },
            {
                "name": "mock",
                "base_url": None,
                "api_key_env": None,
                "model": "mock",
            },
        ]
        self.breakers: Dict[str, CircuitBreaker] = {
            p["name"]: CircuitBreaker(p["name"]) for p in self.providers
        }
        self.client = httpx.AsyncClient(timeout=30.0)

    async def _call_provider(self, provider: Dict[str, Any], prompt: str, context: Dict[str, Any], priority: str) -> str:
        name = provider["name"]
        if name == "mock":
            return f"[MOCK] {prompt[:80]}"
        api_key = os.getenv(provider["api_key_env"])
        if not api_key:
            raise RuntimeError(f"Missing API key for {name} (env {provider['api_key_env']})")
        url = f"{provider['base_url']}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": provider["model"],
            "messages": [
                {"role": "system", "content": json.dumps(context)},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2 if priority == "high" else 0.7,
        }
        start = time.time()
        resp = await self.client.post(url, headers=headers, json=payload)
        latency_ms = int((time.time() - start) * 1000)
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        # estimate tokens (rough)
        tokens = len(prompt.split()) + len(text.split())
        cost = self._estimate_cost(name, tokens)
        self._log_metric(name, latency_ms, tokens, cost)
        return text

    def _estimate_cost(self, provider: str, tokens: int) -> float:
        # placeholder rates per 1k tokens
        rates = {"nvidia": 0.0004, "openrouter": 0.001, "groq": 0.0003, "mock": 0.0}
        return (tokens / 1000) * rates.get(provider, 0.0)

    def _log_metric(self, provider: str, latency_ms: int, tokens: int, cost: float):
        entry = {
            "chain_id": os.getenv("CHAIN_ID", "unknown"),
            "provider_usado": provider,
            "latency_ms": latency_ms,
            "tokens": tokens,
            "custo_estimado": round(cost, 6),
            "timestamp": time.time(),
        }
        try:
            with open(METRICS_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass  # best effort

    async def route(self, prompt: str, context: Optional[Dict[str, Any]] = None, priority: str = "normal") -> str:
        context = context or {}
        chain_id = os.getenv("CHAIN_ID", "unknown")
        context.setdefault("chain_id", chain_id)

        for provider in self.providers:
            name = provider["name"]
            breaker = self.breakers[name]
            if not breaker.can_attempt():
                continue
            try:
                result = await self._call_provider(provider, prompt, context, priority)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                # continue to next provider
        # all failed
        raise RuntimeError("All providers failed")

    async def close(self):
        await self.client.aclose()


def load_providers():
    """Return list of provider configs."""
    router = ProviderRouter()
    return router.providers


def get_agent_group(agent_name: str) -> Optional[str]:
    """Placeholder for agent grouping."""
    return None


def get_agents_in_other_groups(group: str):
    """Placeholder for cross-group agents."""
    return []
