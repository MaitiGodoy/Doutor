import sqlite3
import json
import time
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timezone


_BASE = Path(__file__).parent.parent
DB_DIR = str(_BASE / "data")
DB_PATH = str(_BASE / "data" / "doutor_state.db")

_initialized = False


def get_connection() -> sqlite3.Connection:
    global _initialized
    Path(DB_DIR).mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    if not _initialized:
        init_db()
        _initialized = True
    return conn


def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'pending',
            module TEXT,
            started_at REAL,
            ended_at REAL,
            tokens_used INTEGER DEFAULT 0,
            cost_estimate REAL DEFAULT 0.0,
            metadata_json TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS provider_quotas (
            provider TEXT PRIMARY KEY,
            used_today INTEGER DEFAULT 0,
            daily_limit INTEGER DEFAULT 200,
            last_reset_utc TEXT,
            is_blocked INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS audit_trail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            agent TEXT,
            action TEXT,
            input_hash TEXT,
            output_hash TEXT,
            status TEXT,
            details_json TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS snapshots (
            id TEXT PRIMARY KEY,
            path TEXT,
            created_at REAL,
            size_bytes INTEGER
        );
        CREATE TABLE IF NOT EXISTS artifacts (
            run_id TEXT,
            key TEXT,
            value_json TEXT,
            created_at REAL,
            PRIMARY KEY (run_id, key)
        );
    ''')
    conn.commit()
    conn.close()


def get_run(run_id: str) -> Optional[Dict]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["metadata"] = json.loads(d.pop("metadata_json", "{}"))
        return d
    return None


def save_run(run_id: str, data: Dict):
    conn = get_connection()
    metadata = data.get("metadata", {})
    conn.execute('''
        INSERT OR REPLACE INTO runs (id, status, module, started_at, ended_at, tokens_used, cost_estimate, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        run_id,
        data.get("status", "pending"),
        data.get("module"),
        data.get("started_at"),
        data.get("ended_at"),
        data.get("tokens_used", 0),
        data.get("cost_estimate", 0.0),
        json.dumps(metadata)
    ))
    conn.commit()
    conn.close()


def save_artifact(run_id: str, key: str, value: Any):
    conn = get_connection()
    conn.execute('''
        INSERT OR REPLACE INTO artifacts (run_id, key, value_json, created_at)
        VALUES (?, ?, ?, ?)
    ''', (run_id, key, json.dumps(value, default=str), time.time()))
    conn.commit()
    conn.close()


def get_artifact(run_id: str, key: str) -> Optional[Any]:
    conn = get_connection()
    row = conn.execute("SELECT value_json FROM artifacts WHERE run_id=? AND key=?", (run_id, key)).fetchone()
    conn.close()
    if row:
        return json.loads(row["value_json"])
    return None


def get_provider_quota(provider: str) -> Dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM provider_quotas WHERE provider=?", (provider,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"provider": provider, "used_today": 0, "daily_limit": 200, "last_reset_utc": None, "is_blocked": 0}


def upsert_provider_quota(provider: str, used_today: int, daily_limit: int, last_reset_utc: str, is_blocked: int):
    conn = get_connection()
    conn.execute('''
        INSERT OR REPLACE INTO provider_quotas (provider, used_today, daily_limit, last_reset_utc, is_blocked)
        VALUES (?, ?, ?, ?, ?)
    ''', (provider, used_today, daily_limit, last_reset_utc, is_blocked))
    conn.commit()
    conn.close()


def get_all_provider_quotas() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM provider_quotas").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_audit(agent: str, action: str, input_hash: str, output_hash: str, status: str, details: Dict = None):
    conn = get_connection()
    conn.execute('''
        INSERT INTO audit_trail (timestamp, agent, action, input_hash, output_hash, status, details_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (time.time(), agent, action, input_hash, output_hash, status, json.dumps(details or {})))
    conn.commit()
    conn.close()


def create_snapshot(path: str) -> str:
    snap_id = f"snap_{int(time.time())}"
    conn = get_connection()
    size = 0
    p = Path(path)
    if p.is_file():
        size = p.stat().st_size
    elif p.is_dir():
        size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
    conn.execute('''
        INSERT INTO snapshots (id, path, created_at, size_bytes)
        VALUES (?, ?, ?, ?)
    ''', (snap_id, str(p.resolve()), time.time(), size))
    conn.commit()
    conn.close()
    return snap_id


def daily_backup():
    Path(DB_DIR).mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    backup_path = os.path.join(DB_DIR, f"doutor_state_backup_{date_str}.db")
    shutil.copy2(DB_PATH, backup_path)
    return backup_path


def reset_daily_quotas():
    conn = get_connection()
    conn.execute("UPDATE provider_quotas SET used_today=0, is_blocked=0")
    conn.commit()
    conn.close()