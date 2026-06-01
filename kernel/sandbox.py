import os
import subprocess
import shlex
import time
import logging
import tempfile
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("antimatter.sandbox")

ALLOWED_COMMANDS = {
    "pip", "python", "node", "npm", "git", "ruff", "bandit", "safety",
    "curl", "ls", "cat", "echo", "grep", "find", "head", "tail",
    "wc", "sort", "uniq", "mkdir", "cp", "mv", "touch", "chmod",
    "pytest", "black", "isort", "flake8", "mypy",
    "sleep", "timeout", "date", "whoami", "uname",
}

BLOCKED_PATTERNS = [
    "sudo", "rm -rf /", "rm -rf *", "mkfs", "dd if=",
    "chmod 777", "chmod 777 /", "curl | bash", "wget | sh",
    "wget -O- | sh", "curl -s | bash", "bash <(curl",
    "> /dev/sda", ":(){ :|:& };:", "forkbomb",
    "eval ", "exec(", "__import__", "os.system",
]

SANDBOX_BASE = Path("sandbox")
MAX_PROCESS_TIME = 60
MAX_MEMORY_MB = 256


def _validate_command(cmd_str: str) -> str:
    parts = shlex.split(cmd_str)
    if not parts:
        raise ValueError("Empty command")
    base = os.path.basename(parts[0])
    if base not in ALLOWED_COMMANDS:
        raise ValueError(f"Command '{base}' is not in the allowed list")
    cmd_lower = cmd_str.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in cmd_lower:
            raise ValueError(f"Command contains blocked pattern: {pattern}")
    return cmd_str


def exec_shell(command: str, run_id: str = "default", timeout: int = MAX_PROCESS_TIME) -> Dict:
    run_dir = SANDBOX_BASE / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_file = Path("logs") / f"sandbox_{run_id}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    _validate_command(command)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(run_dir),
            env={**os.environ, "HOME": str(run_dir)},
        )

        output = {
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
            "exit_code": result.returncode,
            "timed_out": False,
        }

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.time()}] CMD: {command}\n")
            f.write(f"  exit: {result.returncode}\n")
            if result.stdout:
                f.write(f"  stdout: {result.stdout[:500]}\n")
            if result.stderr:
                f.write(f"  stderr: {result.stderr[:500]}\n")

        return output

    except subprocess.TimeoutExpired:
        entry = {
            "stdout": "",
            "stderr": f"Command timed out after {timeout}s",
            "exit_code": -1,
            "timed_out": True,
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"[{time.time()}] CMD: {command} [TIMEOUT]\n")
        return entry

    except Exception as e:
        return {
            "stdout": "",
            "stderr": str(e),
            "exit_code": -1,
            "timed_out": False,
        }


def sandbox_path(run_id: str = "default") -> str:
    p = SANDBOX_BASE / run_id
    p.mkdir(parents=True, exist_ok=True)
    return str(p.resolve())


def cleanup_sandbox(run_id: str):
    p = SANDBOX_BASE / run_id
    if p.exists():
        import shutil
        shutil.rmtree(p, ignore_errors=True)
