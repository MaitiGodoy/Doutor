from __future__ import annotations

import asyncio
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from openai import AsyncOpenAI
from kernel.provider_quotas import check_quota, increment_quota, circuit_breaker_status

logger = logging.getLogger("antimatter.router")

ANTI_COLLUSION_GROUPS = [
    ["the_architect", "the_wordsmiths", "the_scaler"],
    ["the_polymath", "the_inspector", "the_empath"],
    ["the_constitution", "the_surgeon", "the_voice"],
    ["the_concierge", "the_producer", "the_ranker"],
]

AGENT_MODEL_MAP = {
    "the_scout":       {"openrouter": "meta-llama/llama-3.3-70b-instruct:free", "groq": "llama-3.1-8b-instant", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_polymath":    {"openrouter": "google/gemma-4-31b-it:free", "groq": "llama-3.3-70b-versatile", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_architect":   {"openrouter": "meta-llama/llama-3.3-70b-instruct:free", "groq": "llama-3.3-70b-versatile", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_constitution":{"openrouter": "google/gemma-4-31b-it:free", "groq": "llama-3.3-70b-versatile", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_surgeon":     {"openrouter": "qwen/qwen3-coder:free", "groq": "qwen/qwen3-32b", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
    "the_wordsmiths":  {"openrouter": "google/gemma-4-31b-it:free", "groq": "llama-3.3-70b-versatile", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_inspector":   {"openrouter": "qwen/qwen3-coder:free", "groq": "qwen/qwen3-32b", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
    "the_scaler":      {"openrouter": "qwen/qwen3-coder:free", "groq": "qwen/qwen3-32b", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
    "the_empath":      {"openrouter": "meta-llama/llama-3.2-3b-instruct:free", "groq": "llama-3.1-8b-instant", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_voice":       {"openrouter": "google/gemma-4-31b-it:free", "groq": "llama-3.1-8b-instant", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_concierge":   {"openrouter": "meta-llama/llama-3.2-3b-instruct:free", "groq": "llama-3.1-8b-instant", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_producer":    {"openrouter": "google/gemma-4-31b-it:free", "groq": "llama-3.1-8b-instant", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
    "the_ranker":      {"openrouter": "meta-llama/llama-3.3-70b-instruct:free", "groq": "llama-3.1-8b-instant", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_lateral":     {"openrouter": "google/gemma-2-9b-it:free", "groq": "gemma2-9b-it", "huggingface": "google/gemma-2-9b-it"},
    "the_omni_aa":     {"openrouter": "qwen/qwen3-coder:free", "groq": "qwen/qwen3-32b", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
    "the_zoiao":       {"openrouter": "qwen/qwen-2.5-vl-72b-instruct:free", "groq": "qwen/qwen3-32b", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
    "the_inner_spark": {"openrouter": "meta-llama/llama-3.2-3b-instruct:free", "groq": "llama-3.1-8b-instant", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_director":    {"openrouter": "meta-llama/llama-3.3-70b-instruct:free", "groq": "llama-3.3-70b-versatile", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_senior_dev":  {"openrouter": "qwen/qwen3-coder:free", "groq": "qwen/qwen3-32b", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
    "the_minimalist":  {"openrouter": "meta-llama/llama-3.2-3b-instruct:free", "groq": "llama-3.1-8b-instant", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_darwin":      {"openrouter": "google/gemma-4-31b-it:free", "groq": "llama-3.1-8b-instant", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_gossip":      {"openrouter": "google/gemma-4-31b-it:free", "groq": "llama-3.3-70b-versatile", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_chronic":          {"openrouter": "google/gemma-2-9b-it:free", "groq": "gemma2-9b-it", "huggingface": "google/gemma-2-9b-it"},
    "the_prompt_architect": {"openrouter": "meta-llama/llama-3.3-70b-instruct:free", "groq": "llama-3.3-70b-versatile", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_planner_alpha":    {"openrouter": "meta-llama/llama-3.3-70b-instruct:free", "groq": "llama-3.3-70b-versatile", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_planner_beta":     {"openrouter": "google/gemma-4-31b-it:free", "groq": "llama-3.3-70b-versatile", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "the_senior_dev_core":  {"openrouter": "qwen/qwen3-coder:free", "groq": "qwen/qwen3-32b", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
    "the_senior_dev_ui":    {"openrouter": "qwen/qwen3-coder:free", "groq": "qwen/qwen3-32b", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
    "the_senior_dev_ops":   {"openrouter": "qwen/qwen3-coder:free", "groq": "qwen/qwen3-32b", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
    "halbert":         {"openrouter": "google/gemma-4-31b-it:free", "groq": "llama-3.1-8b-instant", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "ogilvy":          {"openrouter": "meta-llama/llama-3.3-70b-instruct:free", "groq": "llama-3.3-70b-versatile", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "kennedy":         {"openrouter": "qwen/qwen3-coder:free", "groq": "qwen/qwen3-32b", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
    # Legacy aliases (old internal keys → same mapping as new agent roles)
    "coder":           {"openrouter": "qwen/qwen3-coder:free", "groq": "qwen/qwen3-32b", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
    "planner_a":       {"openrouter": "meta-llama/llama-3.3-70b-instruct:free", "groq": "llama-3.3-70b-versatile", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "planner_b":       {"openrouter": "google/gemma-4-31b-it:free", "groq": "llama-3.3-70b-versatile", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "creator":         {"openrouter": "google/gemma-4-31b-it:free", "groq": "llama-3.3-70b-versatile", "huggingface": "meta-llama/Llama-3.1-8B-Instruct"},
    "auditor":         {"openrouter": "qwen/qwen3-coder:free", "groq": "qwen/qwen3-32b", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
    "producer":        {"openrouter": "google/gemma-4-31b-it:free", "groq": "llama-3.1-8b-instant", "huggingface": "Qwen/Qwen2.5-Coder-32B-Instruct"},
}

@dataclass
class RoleConfig:
    temperature: float
    max_tokens: int

ROLE_DEFAULTS: Dict[str, RoleConfig] = {
    "the_scout":       RoleConfig(temperature=0.4, max_tokens=2048),
    "the_polymath":    RoleConfig(temperature=0.7, max_tokens=3072),
    "the_architect":   RoleConfig(temperature=0.6, max_tokens=3072),
    "the_constitution":RoleConfig(temperature=0.2, max_tokens=2048),
    "the_surgeon":     RoleConfig(temperature=0.1, max_tokens=2048),
    "the_wordsmiths":  RoleConfig(temperature=0.8, max_tokens=4096),
    "the_inspector":   RoleConfig(temperature=0.3, max_tokens=3072),
    "the_scaler":      RoleConfig(temperature=0.4, max_tokens=3072),
    "the_empath":      RoleConfig(temperature=0.6, max_tokens=3072),
    "the_voice":       RoleConfig(temperature=0.7, max_tokens=3072),
    "the_concierge":   RoleConfig(temperature=0.5, max_tokens=2048),
    "the_producer":    RoleConfig(temperature=0.3, max_tokens=4096),
    "the_ranker":      RoleConfig(temperature=0.3, max_tokens=2048),
    "the_lateral":     RoleConfig(temperature=0.75, max_tokens=4096),
    "the_omni_aa":     RoleConfig(temperature=0.1, max_tokens=3000),
    "the_zoiao":       RoleConfig(temperature=0.1, max_tokens=2048),
    "the_inner_spark":    RoleConfig(temperature=0.3, max_tokens=1024),
    "the_prompt_architect": RoleConfig(temperature=0.3, max_tokens=3072),
    "the_planner_alpha":    RoleConfig(temperature=0.1, max_tokens=4096),
    "the_planner_beta":     RoleConfig(temperature=0.1, max_tokens=4096),
    "the_senior_dev_core":  RoleConfig(temperature=0.1, max_tokens=4096),
    "the_senior_dev_ui":    RoleConfig(temperature=0.1, max_tokens=4096),
    "the_senior_dev_ops":   RoleConfig(temperature=0.1, max_tokens=4096),
    "halbert":         RoleConfig(temperature=0.9, max_tokens=3072),
    "ogilvy":          RoleConfig(temperature=0.7, max_tokens=3072),
    "kennedy":         RoleConfig(temperature=0.8, max_tokens=3072),
    # Legacy aliases
    "coder":           RoleConfig(temperature=0.2, max_tokens=4096),
    "planner_a":       RoleConfig(temperature=0.6, max_tokens=3072),
    "planner_b":       RoleConfig(temperature=0.7, max_tokens=3072),
    "creator":         RoleConfig(temperature=0.8, max_tokens=4096),
    "auditor":         RoleConfig(temperature=0.3, max_tokens=3072),
    "producer":        RoleConfig(temperature=0.3, max_tokens=4096),
}

def get_agent_group(agent_role: str) -> int:
    for i, group in enumerate(ANTI_COLLUSION_GROUPS):
        if agent_role in group:
            return i
    return -1

def get_agents_in_other_groups(current_role: str) -> List[str]:
    current_group = get_agent_group(current_role)
    others = []
    for i, group in enumerate(ANTI_COLLUSION_GROUPS):
        if i != current_group:
            others.extend(group)
    return others

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
    providers = []
    or_key = os.getenv("OPENROUTER_API_KEY", "")
    if or_key:
        providers.append(ProviderConfig(
            name="openrouter",
            base_url="https://openrouter.ai/api/v1",
            api_key=or_key,
            priority=1,
            daily_request_limit=200,
            models={
                "the_scout":       "meta-llama/llama-3.3-70b-instruct:free",
                "the_polymath":    "google/gemma-4-31b-it:free",
                "the_architect":   "meta-llama/llama-3.3-70b-instruct:free",
                "the_constitution":"google/gemma-4-31b-it:free",
                "the_surgeon":     "qwen/qwen3-coder:free",
                "the_wordsmiths":  "google/gemma-4-31b-it:free",
                "the_inspector":   "qwen/qwen3-coder:free",
                "the_scaler":      "qwen/qwen3-coder:free",
                "the_empath":      "meta-llama/llama-3.2-3b-instruct:free",
                "the_voice":       "google/gemma-4-31b-it:free",
                "the_concierge":   "meta-llama/llama-3.2-3b-instruct:free",
                "the_producer":    "google/gemma-4-31b-it:free",
                "the_ranker":      "meta-llama/llama-3.3-70b-instruct:free",
                "the_lateral":     "google/gemma-2-9b-it:free",
                "the_omni_aa":     "qwen/qwen3-coder:free",
                "the_zoiao":       "qwen/qwen-2.5-vl-72b-instruct:free",
                "the_inner_spark": "meta-llama/llama-3.2-3b-instruct:free",
                "halbert":         "google/gemma-4-31b-it:free",
                "ogilvy":          "meta-llama/llama-3.3-70b-instruct:free",
                "kennedy":         "qwen/qwen3-coder:free",
            },
            extra_headers={
                "HTTP-Referer": "https://github.com/antimatter-squad",
                "X-Title": "Antimatter Squad Orchestrator",
            },
        ))
    groq_key = os.getenv("GROQ_API_KEY", "")
    if groq_key:
        providers.append(ProviderConfig(
            name="groq",
            base_url="https://api.groq.com/openai/v1",
            api_key=groq_key,
            priority=2,
            daily_request_limit=500,
            models={
                "the_scout":       "llama-3.1-8b-instant",
                "the_polymath":    "llama-3.3-70b-versatile",
                "the_architect":   "llama-3.3-70b-versatile",
                "the_constitution":"llama-3.3-70b-versatile",
                "the_surgeon":     "qwen/qwen3-32b",
                "the_wordsmiths":  "llama-3.3-70b-versatile",
                "the_inspector":   "qwen/qwen3-32b",
                "the_scaler":      "qwen/qwen3-32b",
                "the_empath":      "llama-3.1-8b-instant",
                "the_voice":       "llama-3.1-8b-instant",
                "the_concierge":   "llama-3.1-8b-instant",
                "the_producer":    "llama-3.1-8b-instant",
                "the_ranker":      "llama-3.1-8b-instant",
                "the_lateral":     "gemma2-9b-it",
                "the_omni_aa":     "qwen/qwen3-32b",
                "the_zoiao":       "qwen/qwen3-32b",
                "the_inner_spark": "llama-3.1-8b-instant",
                "halbert":         "llama-3.1-8b-instant",
                "ogilvy":          "llama-3.3-70b-versatile",
                "kennedy":         "qwen/qwen3-32b",
            },
        ))
    hf_key = os.getenv("HUGGINGFACE_API_KEY", "")
    if hf_key:
        providers.append(ProviderConfig(
            name="huggingface",
            base_url="https://router.huggingface.co/v1",
            api_key=hf_key,
            priority=3,
            daily_request_limit=300,
            models={
                "the_scout":       "meta-llama/Llama-3.1-8B-Instruct",
                "the_polymath":    "meta-llama/Llama-3.1-8B-Instruct",
                "the_architect":   "meta-llama/Llama-3.1-8B-Instruct",
                "the_constitution":"meta-llama/Llama-3.1-8B-Instruct",
                "the_surgeon":     "Qwen/Qwen2.5-Coder-32B-Instruct",
                "the_wordsmiths":  "meta-llama/Llama-3.1-8B-Instruct",
                "the_inspector":   "Qwen/Qwen2.5-Coder-32B-Instruct",
                "the_scaler":      "Qwen/Qwen2.5-Coder-32B-Instruct",
                "the_empath":      "meta-llama/Llama-3.1-8B-Instruct",
                "the_voice":       "meta-llama/Llama-3.1-8B-Instruct",
                "the_concierge":   "meta-llama/Llama-3.1-8B-Instruct",
                "the_producer":    "Qwen/Qwen2.5-Coder-32B-Instruct",
                "the_ranker":      "meta-llama/Llama-3.1-8B-Instruct",
                "the_lateral":     "google/gemma-2-9b-it",
                "the_omni_aa":     "Qwen/Qwen2.5-Coder-32B-Instruct",
                "the_zoiao":       "Qwen/Qwen2.5-Coder-32B-Instruct",
                "the_inner_spark": "meta-llama/Llama-3.1-8B-Instruct",
                "halbert":         "meta-llama/Llama-3.1-8B-Instruct",
                "ogilvy":          "meta-llama/Llama-3.1-8B-Instruct",
                "kennedy":         "Qwen/Qwen2.5-Coder-32B-Instruct",
            },
        ))
    fireworks_key = os.getenv("FIREWORKS_API_KEY", "")
    if fireworks_key:
        providers.append(ProviderConfig(
            name="fireworks",
            base_url="https://api.fireworks.ai/inference/v1",
            api_key=fireworks_key,
            priority=4,
            daily_request_limit=200,
            models={role: "accounts/fireworks/models/mixtral-8x7b-instruct" for role in AGENT_MODEL_MAP},
        ))
    together_key = os.getenv("TOGETHER_API_KEY", "")
    if together_key:
        providers.append(ProviderConfig(
            name="together",
            base_url="https://api.together.xyz/v1",
            api_key=together_key,
            priority=5,
            daily_request_limit=200,
            models={role: "meta-llama/Meta-Llama-3-70B-Instruct-Turbo" for role in AGENT_MODEL_MAP},
        ))
    ollama_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    providers.append(ProviderConfig(
        name="ollama_local",
        base_url=f"{ollama_url}/v1",
        api_key="ollama",
        priority=6,
        daily_request_limit=1000,
        models={role: "codellama:7b" for role in AGENT_MODEL_MAP},
    ))
    providers.sort(key=lambda p: p.priority)
    return providers


PROVIDER_CHAIN_META = [
    {"name": "openrouter", "model": "qwen-2.5-coder-32b-instruct", "priority": 1, "cost_per_1k": 0.0003},
    {"name": "groq", "model": "llama-3.1-8b-instant", "priority": 2, "cost_per_1k": 0.00005},
    {"name": "huggingface", "model": "microsoft/phi-3-mini", "priority": 3, "cost_per_1k": 0.0},
    {"name": "fireworks", "model": "accounts/fireworks/models/mixtral-8x7b-instruct", "priority": 4, "cost_per_1k": 0.0002},
    {"name": "together", "model": "meta-llama/Meta-Llama-3-70B-Instruct-Turbo", "priority": 5, "cost_per_1k": 0.0003},
    {"name": "ollama_local", "model": "codellama:7b", "priority": 6, "cost_per_1k": 0.0},
]

class ProviderRouter:
    def __init__(self, providers: Optional[List[ProviderConfig]] = None, db_path: str = "data/provider_quotas.db"):
        self.providers = providers or load_providers()
        self._clients: Dict[str, AsyncOpenAI] = {}
        self._health_cache_ttl = 60
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._sqlite_conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_sqlite()
        self._reset_if_new_day()
        if not self.providers:
            raise RuntimeError("No AI providers configured.")
        logger.info(f"ProviderRouter initialized with {len(self.providers)} providers: {[p.name for p in self.providers]}")

    def _init_sqlite(self):
        self._sqlite_conn.execute("""CREATE TABLE IF NOT EXISTS quota_tracker (
            provider TEXT PRIMARY KEY, used_today REAL DEFAULT 0, limit_daily REAL DEFAULT 50000,
            is_blocked BOOLEAN DEFAULT 0, last_reset TEXT
        )""")
        for p in PROVIDER_CHAIN_META:
            self._sqlite_conn.execute("INSERT OR IGNORE INTO quota_tracker (provider) VALUES (?)", (p["name"],))
        self._sqlite_conn.commit()

    def _reset_if_new_day(self):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        cursor = self._sqlite_conn.execute("SELECT last_reset FROM quota_tracker LIMIT 1")
        row = cursor.fetchone()
        if not row or row[0] != today:
            self._sqlite_conn.execute("UPDATE quota_tracker SET used_today=0, is_blocked=0, last_reset=?", (today,))
            self._sqlite_conn.commit()
            logger.info("[ProviderRouter] Quotas resetadas para novo dia UTC.")

    def get_healthy_providers(self) -> List[str]:
        self._reset_if_new_day()
        rows = self._sqlite_conn.execute(
            "SELECT provider, is_blocked, used_today, limit_daily FROM quota_tracker"
        ).fetchall()
        return [r[0] for r in rows if not r[1] and r[2] < r[3]]

    def select_model(self, task_complexity: str, budget_remaining: float) -> Dict:
        self._reset_if_new_day()
        healthy = self.get_healthy_providers()
        if not healthy:
            raise RuntimeError("Nenhum provider disponível. Quota esgotada ou bloqueada.")
        if task_complexity == "high" and budget_remaining > 1000:
            candidates = [p for p in PROVIDER_CHAIN_META if p["name"] in healthy and p["priority"] <= 2]
        elif task_complexity == "low" or budget_remaining < 500:
            candidates = [p for p in PROVIDER_CHAIN_META if p["name"] in healthy and p["priority"] >= 3]
        else:
            candidates = [p for p in PROVIDER_CHAIN_META if p["name"] in healthy]
        selected = candidates[0] if candidates else PROVIDER_CHAIN_META[0]
        return {
            "provider": selected["name"],
            "model": selected["model"],
            "api_key_env": f"{selected['name'].upper()}_API_KEY",
            "cost_per_1k": selected["cost_per_1k"],
        }

    def record_usage(self, provider: str, tokens: int = 0, cost: float = 0.0):
        self._sqlite_conn.execute(
            "UPDATE quota_tracker SET used_today = used_today + ? WHERE provider = ?",
            (tokens, provider),
        )
        self._sqlite_conn.execute(
            "UPDATE quota_tracker SET is_blocked = 1 WHERE provider = ? AND used_today >= limit_daily",
            (provider,),
        )
        self._sqlite_conn.commit()

    def close(self):
        self._sqlite_conn.close()

    def _get_client(self, provider: ProviderConfig) -> AsyncOpenAI:
        if provider.name not in self._clients:
            self._clients[provider.name] = AsyncOpenAI(
                api_key=provider.api_key, base_url=provider.base_url, max_retries=0,
                default_headers=provider.extra_headers or None,
            )
        return self._clients[provider.name]

    async def health_check(self, provider: ProviderConfig) -> bool:
        now = time.time()
        if now - provider.last_check < self._health_cache_ttl:
            return provider.healthy
        try:
            client = self._get_client(provider)
            first_model = list(provider.models.values())[0]
            resp = await asyncio.wait_for(
                client.chat.completions.create(model=first_model, messages=[{"role": "user", "content": "ping"}], max_tokens=5, temperature=0),
                timeout=15,
            )
            provider.healthy = True
            provider.consecutive_failures = 0
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str:
                provider.healthy = True
                provider.consecutive_failures = 0
            else:
                provider.healthy = False
                provider.consecutive_failures += 1
                logger.warning(f"Health check FAIL: {provider.name}: {e}")
        provider.last_check = now
        return provider.healthy

    async def health_check_all(self) -> Dict[str, bool]:
        results = {}
        tasks = [self.health_check(p) for p in self.providers]
        checks = await asyncio.gather(*tasks, return_exceptions=True)
        for p, result in zip(self.providers, checks):
            results[p.name] = result if isinstance(result, bool) else False
        return results

    def get_model_for_agent(self, agent_role: str, provider_name: str) -> Optional[str]:
        model_map = AGENT_MODEL_MAP.get(agent_role, {})
        return model_map.get(provider_name)

    def get_provider_for_agent(self, agent_role: str, exclude_names: Optional[List[str]] = None) -> Tuple[ProviderConfig, str, AsyncOpenAI]:
        exclude = exclude_names or []
        for provider in self.providers:
            if provider.name in exclude:
                continue
            quota_check = check_quota(provider.name)
            if not quota_check["allowed"]:
                continue
            if not provider.healthy:
                if time.time() - provider.last_check > 30:
                    provider.healthy = True
                    provider.consecutive_failures = 0
                else:
                    continue
            model_id = self.get_model_for_agent(agent_role, provider.name) or provider.models.get(agent_role)
            if model_id:
                return provider, model_id, self._get_client(provider)
        circuit = circuit_breaker_status()
        if circuit.get("all_blocked"):
            raise RuntimeError(f"CIRCUIT BREAKER: All providers blocked. Wait for daily reset.")
        available = [p for p in self.providers if p.name not in exclude]
        p = available[0] if available else self.providers[0]
        model_id = self.get_model_for_agent(agent_role, p.name) or list(p.models.values())[0]
        logger.error(f"All providers exhausted for {agent_role}, forcing {p.name}/{model_id}")
        return p, model_id, self._get_client(p)

    def get_diverse_providers(self, agent_roles: List[str]) -> Dict[str, Tuple[str, str]]:
        assigned = {}
        used_providers = set()
        for role in agent_roles:
            for p in self.providers:
                if p.name in used_providers:
                    continue
                model_id = self.get_model_for_agent(role, p.name) or p.models.get(role)
                if model_id:
                    assigned[role] = (p.name, model_id)
                    used_providers.add(p.name)
                    break
            if role not in assigned:
                for p in self.providers:
                    if p.name not in used_providers or len(used_providers) == len(self.providers):
                        model_id = self.get_model_for_agent(role, p.name) or list(p.models.values())[0]
                        if model_id:
                            assigned[role] = (p.name, model_id)
                            break
        return assigned

    def get_best_provider(self, role: str, exclude_names: Optional[List[str]] = None) -> Tuple[ProviderConfig, str, AsyncOpenAI]:
        return self.get_provider_for_agent(role, exclude_names)

    def select_provider(self, task_type: str) -> Tuple[ProviderConfig, str, AsyncOpenAI]:
        healthy = self.get_healthy_providers()
        if not healthy:
            raise RuntimeError("No providers available.")

        if task_type == "simple":
            candidates = ["groq", "huggingface", "ollama_local"]
            for c in candidates:
                if c in healthy:
                    return self.get_provider_for_agent("the_concierge")
            return self.get_provider_for_agent("the_concierge")
        else:
            candidates = ["openrouter", "groq", "fireworks", "together"]
            for c in candidates:
                if c in healthy:
                    return self.get_provider_for_agent("the_senior_dev_core")
            return self.get_provider_for_agent("the_senior_dev_core")

    def mark_success(self, provider: ProviderConfig) -> None:
        provider.consecutive_failures = 0
        provider.daily_request_count += 1
        increment_quota(provider.name)

    def mark_failure(self, provider: ProviderConfig) -> None:
        provider.consecutive_failures += 1
        provider.last_check = time.time()
        if provider.consecutive_failures >= 3:
            provider.healthy = False
            logger.warning(f"Provider {provider.name} marked UNHEALTHY")

    def budget_status(self) -> Dict[str, Any]:
        return {p.name: {"healthy": p.healthy, "requests_used": p.daily_request_count, "requests_limit": p.daily_request_limit, "pct_used": round(p.daily_request_count / max(1, p.daily_request_limit) * 100, 1), "consecutive_failures": p.consecutive_failures} for p in self.providers}

    def reset_daily_counts(self) -> None:
        for p in self.providers:
            p.daily_request_count = 0
            p.healthy = True
            p.consecutive_failures = 0
