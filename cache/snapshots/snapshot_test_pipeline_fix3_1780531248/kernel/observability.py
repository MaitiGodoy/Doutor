import os, json, sqlite3, time
from pathlib import Path
from typing import Dict, List

class ObservabilityDB:
    def __init__(self, db_path: str = "data/observability.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_schema()

    def _init_schema(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS traces (
            run_id TEXT, role TEXT, timestamp REAL, tokens INT, cost REAL,
            latency_ms INT, status TEXT, model TEXT, metadata TEXT
        )""")
        self.conn.commit()

    def ingest_jsonl(self, log_dir: str = "logs"):
        ingested = 0
        for lf in Path(log_dir).glob("*_audit.jsonl"):
            with open(lf, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        self.conn.execute(
                            "INSERT INTO traces VALUES (?,?,?,?,?,?,?,?,?)",
                            (
                                entry.get("run_id"), entry.get("role"), entry.get("timestamp"),
                                entry.get("tokens", 0), entry.get("cost", 0.0),
                                entry.get("latency_ms", 0), entry.get("status"),
                                entry.get("model"), json.dumps(entry.get("metadata", {}))
                            )
                        )
                        ingested += 1
                    except:
                        continue
        self.conn.commit()
        return {"status": "ingested", "rows": ingested}

    def query(self, run_id: str = None, role: str = None, limit: int = 50) -> List[Dict]:
        query = "SELECT * FROM traces WHERE 1=1"
        params = []
        if run_id:
            query += " AND run_id=?"
            params.append(run_id)
        if role:
            query += " AND role=?"
            params.append(role)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(query, params).fetchall()
        cols = [desc[0] for desc in self.conn.execute("PRAGMA table_info(traces)").fetchall()]
        return [dict(zip(cols, r)) for r in rows]
