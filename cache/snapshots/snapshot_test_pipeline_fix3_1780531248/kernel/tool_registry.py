import json, logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("doutor.tool_registry")

class ToolRegistry:
    def __init__(self, registry_path: str = "data/tool_registry.json"):
        self.path = Path(registry_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.registry = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"tools": {}}

    def register(self, name: str, version: str, healthcheck_cmd: str, fallback: str = None):
        self.registry["tools"][name] = {
            "version": version,
            "status": "unknown",
            "healthcheck": healthcheck_cmd,
            "fallback": fallback,
            "last_check": None
        }
        self._save()

    def check_health(self, name: str) -> dict:
        import subprocess
        tool = self.registry["tools"].get(name)
        if not tool:
            return {"status": "not_found"}
        try:
            proc = subprocess.run(tool["healthcheck"], shell=True, capture_output=True, text=True, timeout=5)
            is_healthy = proc.returncode == 0
            tool["status"] = "healthy" if is_healthy else "degraded"
            tool["last_check"] = self._now()
            self._save()
            return {"status": tool["status"], "fallback": tool.get("fallback")}
        except Exception as e:
            tool["status"] = "unhealthy"
            tool["last_check"] = self._now()
            self._save()
            return {"status": "unhealthy", "error": str(e), "fallback": tool.get("fallback")}

    def _save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.registry, f, indent=2)

    def _now(self) -> float:
        import time
        return time.time()
