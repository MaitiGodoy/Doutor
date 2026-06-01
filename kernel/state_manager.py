import os
import json
import time
import sqlite3
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

DB_PATH = Path("data/doutor.db")
_local = threading.local()


class StateManager:
    def __init__(self, db_path: str = None):
        self.db_path = Path(db_path or DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        if not hasattr(_local, "conn") or _local.conn is None:
            _local.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            _local.conn.row_factory = sqlite3.Row
            _local.conn.execute("PRAGMA journal_mode=WAL")
            _local.conn.execute("PRAGMA busy_timeout=5000")
        return _local.conn

    def init_db(self):
        conn = self.get_connection()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'pending',
                module TEXT,
                started_at REAL,
                ended_at REAL,
                tokens_used INTEGER DEFAULT 0,
                cost_estimate REAL DEFAULT 0.0,
                metadata TEXT DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS checkpoints (
                checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                phase TEXT NOT NULL,
                status TEXT DEFAULT 'success',
                data TEXT DEFAULT '{}',
                created_at REAL DEFAULT (strftime('%s','now')),
                FOREIGN KEY (run_id) REFERENCES runs(run_id)
            );
            CREATE TABLE IF NOT EXISTS audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                event TEXT NOT NULL,
                input_hash TEXT,
                output_hash TEXT,
                status TEXT DEFAULT 'ok',
                created_at REAL DEFAULT (strftime('%s','now'))
            );
            CREATE TABLE IF NOT EXISTS provider_quotas (
                provider TEXT PRIMARY KEY,
                used_today INTEGER DEFAULT 0,
                daily_limit INTEGER DEFAULT 200,
                blocked INTEGER DEFAULT 0,
                last_reset_date TEXT
            );
            CREATE TABLE IF NOT EXISTS phase_budget (
                phase TEXT NOT NULL,
                run_id TEXT NOT NULL,
                tokens_consumed INTEGER DEFAULT 0,
                max_tokens INTEGER DEFAULT 8000,
                PRIMARY KEY (phase, run_id)
            );
        """)
        conn.commit()

    def save_run(self, run_id: str, data: Dict):
        conn = self.get_connection()
        now = time.time()
        conn.execute("""
            INSERT INTO runs (run_id, status, module, started_at, ended_at, tokens_used, cost_estimate, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status=excluded.status, ended_at=excluded.ended_at,
                tokens_used=excluded.tokens_used, cost_estimate=excluded.cost_estimate,
                metadata=excluded.metadata
        """, (
            run_id, data.get("status", "running"), data.get("module", ""),
            data.get("started_at", now), data.get("ended_at"),
            data.get("tokens_used", 0), data.get("cost_estimate", 0.0),
            json.dumps(data.get("metadata", {}))
        ))
        conn.commit()

    def get_run(self, run_id: str) -> Optional[Dict]:
        conn = self.get_connection()
        row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        if row:
            d = dict(row)
            d["metadata"] = json.loads(d.get("metadata", "{}"))
            return d
        return None

    def save_checkpoint(self, run_id: str, phase: str, data: Dict = None):
        conn = self.get_connection()
        conn.execute(
            "INSERT INTO checkpoints (run_id, phase, data) VALUES (?, ?, ?)",
            (run_id, phase, json.dumps(data or {}))
        )
        conn.commit()

    def load_checkpoint(self, run_id: str, phase: str = None) -> Optional[Dict]:
        conn = self.get_connection()
        if phase:
            row = conn.execute(
                "SELECT * FROM checkpoints WHERE run_id=? AND phase=? ORDER BY checkpoint_id DESC LIMIT 1",
                (run_id, phase)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM checkpoints WHERE run_id=? ORDER BY checkpoint_id DESC LIMIT 1",
                (run_id,)
            ).fetchone()
        if row:
            d = dict(row)
            d["data"] = json.loads(d.get("data", "{}"))
            return d
        return None

    def log_audit(self, source: str, event: str, input_hash: str = "", output_hash: str = "", status: str = "ok"):
        conn = self.get_connection()
        conn.execute(
            "INSERT INTO audit_trail (source, event, input_hash, output_hash, status) VALUES (?, ?, ?, ?, ?)",
            (source, event, input_hash, output_hash, status)
        )
        conn.commit()

    def get_run_history(self, limit: int = 20) -> List[Dict]:
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def upsert_provider_quota(self, provider: str, used_today: int = None, daily_limit: int = None, blocked: int = None):
        conn = self.get_connection()
        existing = conn.execute("SELECT * FROM provider_quotas WHERE provider=?", (provider,)).fetchone()
        if existing:
            updates = {}
            if used_today is not None: updates["used_today"] = used_today
            if daily_limit is not None: updates["daily_limit"] = daily_limit
            if blocked is not None: updates["blocked"] = blocked
            if updates:
                set_clause = ", ".join(f"{k}=?" for k in updates)
                vals = list(updates.values()) + [provider]
                conn.execute(f"UPDATE provider_quotas SET {set_clause} WHERE provider=?", vals)
        else:
            conn.execute(
                "INSERT INTO provider_quotas (provider, used_today, daily_limit, blocked) VALUES (?, ?, ?, ?)",
                (provider, used_today or 0, daily_limit or 200, blocked or 0)
            )
        conn.commit()

    def get_all_provider_quotas(self) -> List[Dict]:
        conn = self.get_connection()
        rows = conn.execute("SELECT * FROM provider_quotas").fetchall()
        return [dict(r) for r in rows]

    def reset_daily_quotas(self):
        conn = self.get_connection()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        conn.execute("UPDATE provider_quotas SET used_today=0, blocked=0, last_reset_date=?", (today,))
        conn.commit()

    def daily_backup(self) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        backup_dir = Path("data/backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"doutor_{today}.db"
        conn = self.get_connection()
        conn.execute(f"VACUUM INTO '{backup_path}'")
        return str(backup_path)

    def close(self):
        if hasattr(_local, "conn") and _local.conn:
            _local.conn.close()
            _local.conn = None
