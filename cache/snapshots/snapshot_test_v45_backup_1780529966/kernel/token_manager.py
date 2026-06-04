import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger("doutor.token_manager")

PHASE_BUDGETS = {
    "briefing": 4000,
    "strategy": 8000,
    "governance_1": 2000,
    "creation": 12000,
    "governance_2": 2000,
    "voice": 4000,
    "seo": 6000,
    "dual_output": 8000,
    "quality": 4000,
    "governance_3": 2000,
    "optimization": 4000,
    "design": 4000,
    "governance_4": 2000,
    "concierge": 2000,
    "inner_spark": 2000,
}

PROVIDER_PRIORITY = ["openrouter", "groq", "huggingface", "together", "fireworks"]


class TokenManager:
    def __init__(self, db_path: str = "data/doutor.db"):
        self.audit_log = Path("logs/token_audit.jsonl")
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
        self._db_path = db_path
        self._provider_failures: Dict[str, int] = {}
        self._provider_successes: Dict[str, int] = {}

    def _get_quotas(self) -> Dict[str, Dict]:
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM provider_quotas").fetchall()
        conn.close()
        quotas = {}
        for r in rows:
            d = dict(r)
            quotas[d["provider"]] = {"used": d["used_today"], "limit": d["daily_limit"], "blocked": d["blocked"]}
        return quotas

    def _update_quota(self, provider: str, used: int):
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        conn.execute("UPDATE provider_quotas SET used_today=? WHERE provider=?", (used, provider))
        conn.commit()
        conn.close()

    def route_with_budget(self, phase: str, role: str, payload: Any) -> Dict:
        start = time.time()
        max_tokens = PHASE_BUDGETS.get(phase, 4000)
        quotas = self._get_quotas()
        entry = {"timestamp": start, "phase": phase, "role": role, "status": "pending"}

        chosen_provider = None
        for provider in PROVIDER_PRIORITY:
            q = quotas.get(provider, {"used": 0, "limit": 200, "blocked": 0})
            if q.get("blocked", 0):
                continue
            if q["used"] >= q["limit"]:
                continue
            chosen_provider = provider
            break

        if not chosen_provider:
            entry["status"] = "blocked"
            entry["reason"] = "all_providers_exhausted_or_blocked"
            self._log(entry)
            return {"status": "blocked", "reason": "All providers exhausted or blocked", "phase": phase}

        try:
            from kernel.llm_client import call_llm
            result = call_llm(role, "", str(payload) if not isinstance(payload, str) else payload)
            elapsed = time.time() - start
            tokens = result.get("tokens", max_tokens // 2)
            new_used = quotas[chosen_provider]["used"] + 1
            self._update_quota(chosen_provider, new_used)
            self._provider_successes[chosen_provider] = self._provider_successes.get(chosen_provider, 0) + 1
            entry["status"] = "success"
            entry["provider"] = chosen_provider
            entry["tokens"] = tokens
            entry["elapsed_ms"] = int(elapsed * 1000)
            self._log(entry)
            return {
                "status": "success",
                "provider": chosen_provider,
                "result": result,
                "tokens_used": tokens,
                "elapsed_ms": int(elapsed * 1000),
            }
        except Exception as e:
            self._provider_failures[chosen_provider] = self._provider_failures.get(chosen_provider, 0) + 1
            entry["status"] = "error"
            entry["provider"] = chosen_provider
            entry["error"] = str(e)
            self._log(entry)
            if self._provider_failures.get(chosen_provider, 0) >= 3:
                self._block_provider(chosen_provider)
            for fallback in PROVIDER_PRIORITY:
                if fallback == chosen_provider:
                    continue
                q = quotas.get(fallback, {"used": 0, "limit": 200, "blocked": 0})
                if q.get("blocked", 0):
                    continue
                if q["used"] >= q["limit"]:
                    continue
                try:
                    from kernel.llm_client import call_llm
                    fallback_result = call_llm(role, "", str(payload) if not isinstance(payload, str) else payload)
                    new_used = quotas[fallback]["used"] + 1
                    self._update_quota(fallback, new_used)
                    self._provider_successes[fallback] = self._provider_successes.get(fallback, 0) + 1
                    entry["status"] = "success_fallback"
                    entry["provider"] = fallback
                    self._log(entry)
                    return {
                        "status": "success",
                        "provider": fallback,
                        "result": fallback_result,
                        "tokens_used": 0,
                        "elapsed_ms": int((time.time() - start) * 1000),
                        "fallback": True,
                    }
                except Exception:
                    self._provider_failures[fallback] = self._provider_failures.get(fallback, 0) + 1
                    continue
            return {"status": "error", "reason": str(e), "phase": phase}

    def get_budget_status(self) -> Dict:
        quotas = self._get_quotas()
        total_used = sum(q["used"] for q in quotas.values())
        total_limit = sum(q["limit"] for q in quotas.values())
        return {
            "quotas": quotas,
            "total_used_today": total_used,
            "total_daily_limit": total_limit,
            "usage_pct": round(total_used / max(total_limit, 1) * 100, 1),
            "blocked_providers": [p for p, q in quotas.items() if q.get("blocked")],
            "failures": self._provider_failures,
            "successes": self._provider_successes,
        }

    def reset_daily_quotas(self):
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        conn.execute("UPDATE provider_quotas SET used_today=0, blocked=0, last_reset_date=?", (today,))
        conn.commit()
        conn.close()
        self._provider_failures.clear()
        self._provider_successes.clear()
        logger.info("Daily quotas reset via TokenManager")

    def _block_provider(self, provider: str):
        import sqlite3
        conn = sqlite3.connect(self._db_path)
        conn.execute("UPDATE provider_quotas SET blocked=1 WHERE provider=?", (provider,))
        conn.commit()
        conn.close()
        logger.warning(f"Provider blocked due to failures: {provider}")

    def _log(self, entry: Dict):
        try:
            with open(self.audit_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass
