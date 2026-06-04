import json, hashlib
from pathlib import Path

class SemanticMemory:
    def __init__(self, index_path: str = "cache/memory_index.json"):
        self.index_path = Path(index_path)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.index = self._load()

    def _load(self) -> dict:
        if self.index_path.exists():
            with open(self.index_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"entries": []}

    def store(self, run_id: str, summary: str, tags: list):
        entry = {
            "run_id": run_id,
            "summary": summary,
            "tags": tags,
            "hash": hashlib.md5(summary.encode()).hexdigest(),
            "timestamp": self._now()
        }
        self.index["entries"].append(entry)
        self._save()

    def retrieve(self, query_tags: list, limit: int = 3) -> list:
        matches = [e for e in self.index["entries"] if any(t in e["tags"] for t in query_tags)]
        matches.sort(key=lambda x: x["timestamp"], reverse=True)
        return matches[:limit]

    def _save(self):
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(self.index, f, indent=2)

    def _now(self) -> float:
        import time
        return time.time()
