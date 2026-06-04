import time
import sqlite3
import logging
import os
from typing import Dict, List
from pathlib import Path

from kernel.state_manager import StateManager, DB_PATH
from kernel.provider_quotas import get_all_quotas, circuit_breaker_status

sm = StateManager()

logger = logging.getLogger("antimatter.health")

_start_time = time.time()


def get_uptime() -> int:
    return int(time.time() - _start_time)


def check_db() -> bool:
    try:
        conn = sm.get_connection()
        conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        return False


def check_disk() -> Dict:
    data_dir = Path("data")
    logs_dir = Path("logs")
    db_path = sm.db_path
    return {
        "data_exists": data_dir.exists(),
        "log_exists": logs_dir.exists(),
        "db_size_bytes": os.path.getsize(db_path) if os.path.exists(db_path) else 0,
    }


def health_status() -> Dict:
    db_ok = check_db()
    quotas = get_all_quotas()
    circuit = circuit_breaker_status()

    return {
        "status": "ok" if db_ok else "degraded",
        "uptime_sec": get_uptime(),
        "db_connected": db_ok,
        "providers_healthy": [q["provider"] for q in quotas if not q.get("is_blocked") and q["used_today"] < q.get("daily_limit", 200)],
        "quota_remaining_pct": round(
            sum(max(0, q.get("daily_limit", 0) - q["used_today"]) for q in quotas)
            / max(1, sum(q.get("daily_limit", 0) for q in quotas)) * 100, 1
        ) if quotas else 0.0,
        "circuit_breaker": circuit,
        "disk": check_disk(),
        "timestamp_utc": time.time(),
    }


def auto_recover():
    if not check_db():
        date_str = time.strftime("%Y%m%d", time.gmtime())
        backup_path = f"data/doutor_state_backup_{date_str}.db"
        if os.path.exists(backup_path):
            import shutil
            shutil.copy2(backup_path, sm.db_path)
            logger.info(f"DB auto-recovered from {backup_path}")
            return True
        logger.error("DB corrupted and no backup available")
        return False
    return True
