"""
NemoClawSandbox – Enhanced sandbox with NemoClaw policy engine.
Advanced firewall, regex blacklist, resource monitoring.
Extends base NemoClawSandbox with policy enforcement.
Zero stubs. 100% funcional.
"""
import json
import os
import re
import time
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.sandbox import NemoClawSandbox as BaseSandbox

BASE_DIR = Path(__file__).resolve().parents[2]
LOG_PATH = BASE_DIR / "logs" / "sandbox_nemoclaw.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# Default blacklist patterns
BLACKLIST_PATTERNS = {
    "file_operations": [r"os\.remove", r"os\.unlink", r"shutil\.rmtree", r"pathlib\.*\.unlink", r"pathlib\.*\.rmdir"],
    "network_access": [r"urllib\.request", r"requests\.", r"httpx\.", r"aiohttp\.", r"socket\.", r"ftplib\.", r"telnetlib"],
    "subprocess": [r"subprocess\.", r"os\.system", r"os\.popen", r"pty\.spawn", r"pexpect\.", r"sh\."],
    "code_execution": [r"eval\s*\(", r"exec\s*\(", r"compile\s*\(", r"__import__", r"importlib\.", r"pickle\.loads"],
    "environment_access": [r"os\.environ", r"os\.getenv", r"os\.putenv", r"os\.listdir", r"os\.walk"],
    "dangerous_modules": [r"ctypes\.", r"signal\.", r"multiprocessing\.", r"threading\.", r"asyncio\.create_subprocess"],
}

DEFAULT_BLACKLIST = [
    r"(?i)(sudo|rm\s+-rf|dd\s+if=|mkfs\.|fdisk|shutdown|reboot|chmod\s+777)",
    r"(?i)(SELECT\s+.*\s+FROM|DROP\s+TABLE|DELETE\s+FROM|INSERT\s+INTO|UPDATE\s+.*SET)",
    r"(?i)(http://|https://|ftp://)\s*(?!localhost|127\.0\.0\.1|0\.0\.0\.0)",
    r"\.\./\.\./|/etc/passwd|/etc/shadow|/proc/",
]


class NemoClawSandbox(BaseSandbox):
    """Enhanced sandbox with NemoClaw policy engine and firewall."""

    def __init__(self, policies: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.policies = policies or {}
        self.blacklist_patterns = BLACKLIST_PATTERNS.copy()
        self.custom_blacklist = DEFAULT_BLACKLIST.copy()
        self._load_custom_policies()
        self._monitor: Dict[str, Any] = {"executions": 0, "blocks": 0, "warnings": 0}

    def _load_custom_policies(self):
        extra = self.policies.get("blacklist_patterns", {})
        for category, patterns in extra.items():
            if isinstance(patterns, list):
                self.blacklist_patterns[category] = patterns
        extra_regex = self.policies.get("custom_blacklist", [])
        if isinstance(extra_regex, list):
            self.custom_blacklist.extend(extra_regex)

    def add_blacklist(self, pattern: str) -> None:
        self.custom_blacklist.append(pattern)

    def add_policy(self, name: str, patterns: List[str]) -> None:
        self.blacklist_patterns[name] = patterns

    def check_code(self, code: str) -> Dict[str, Any]:
        issues = []
        blocks = []
        for category, patterns in self.blacklist_patterns.items():
            for p in patterns:
                matches = re.findall(p, code)
                if matches:
                    severity = "block" if category in ("subprocess", "file_operations", "code_execution") else "warn"
                    issues.append({"policy": category, "pattern": p, "matches": matches, "severity": severity})
                    if severity == "block":
                        blocks.append(category)
        for p in self.custom_blacklist:
            matches = re.findall(p, code)
            if matches:
                issues.append({"policy": "custom_blacklist", "pattern": p, "matches": matches, "severity": "block"})
                blocks.append("custom")
        return {
            "allowed": len(blocks) == 0,
            "blocked_categories": list(set(blocks)),
            "issues": issues,
            "issue_count": len(issues),
        }

    def run(self, tool: str, **kwargs: Any) -> Dict[str, Any]:
        code = kwargs.get("code", "")
        if code:
            check = self.check_code(code)
            if not check["allowed"]:
                self._monitor["blocks"] += 1
                self._log("blocked", {"tool": tool, "reason": check["blocked_categories"], "issues": check["issues"]})
                return {"success": False, "error": f"blocked_by_policy: {check['blocked_categories']}", "policy_check": check}
            self._monitor["warnings"] += len([i for i in check["issues"] if i["severity"] == "warn"])
        result = super().run(tool, **kwargs)
        self._monitor["executions"] += 1
        if isinstance(result, dict) and result.get("success"):
            self._log("allowed", {"tool": tool, "policy_check": check if code else None})
        return result

    def run_code(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        check = self.check_code(code)
        if not check["allowed"]:
            self._monitor["blocks"] += 1
            self._log("blocked", {"tool": "run_code", "reason": check["blocked_categories"]})
            return {"success": False, "error": f"blocked_by_policy: {check['blocked_categories']}", "policy_check": check}
        self._monitor["executions"] += 1
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            fpath = f.name
        try:
            start = time.time()
            proc = subprocess.run(["python3", fpath], capture_output=True, text=True, timeout=timeout)
            elapsed = round((time.time() - start) * 1000, 2)
            result = {
                "success": proc.returncode == 0,
                "output": proc.stdout,
                "error": proc.stderr,
                "returncode": proc.returncode,
                "elapsed_ms": elapsed,
            }
            if not result["success"]:
                self._log("error", {"tool": "run_code", "error": proc.stderr[:500]})
            return result
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"timeout after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            Path(fpath).unlink(missing_ok=True)

    def resource_usage(self) -> Dict[str, Any]:
        try:
            import psutil
            proc = psutil.Process()
            return {
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_mb": round(proc.memory_info().rss / 1024 / 1024, 2),
                "open_fds": proc.num_fds(),
                "threads": proc.num_threads(),
            }
        except ImportError:
            import os as _os
            return {"error": "psutil not installed", "pid": _os.getpid()}

    def monitor_stats(self) -> Dict[str, Any]:
        return {**self._monitor, "timestamp": time.time()}

    def reset_monitor(self) -> None:
        self._monitor = {"executions": 0, "blocks": 0, "warnings": 0}

    def _log(self, action: str, payload: Dict[str, Any]) -> None:
        entry = {"timestamp": time.time(), "action": action, "payload": payload}
        try:
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass