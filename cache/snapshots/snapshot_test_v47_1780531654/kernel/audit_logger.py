import os
import json
import time
import logging
from pathlib import Path

logger = logging.getLogger("doutor.audit_logger")

class AuditLogger:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log(self, role: str, run_id: str, prompt_hash: str, tokens: int, cost: float, latency_ms: int, status: str, model: str):
        entry = {
            "timestamp": time.time(),
            "role": role,
            "run_id": run_id,
            "prompt_hash": prompt_hash,
            "tokens": tokens,
            "cost": cost,
            "latency_ms": latency_ms,
            "status": status,
            "model": model,
        }
        path = self.log_dir / f"{role}_audit.jsonl"
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except OSError as e:
            logger.warning(f"AuditLogger failed to write {path}: {e}")
