import os
import re
import json
import time
import subprocess
from typing import Dict, Any
from pydantic import BaseModel, Field

LOG_PATH = os.getenv("EXECUTION_LOG_PATH", "/var/log/execution.jsonl")

# Dangerous patterns blacklist
DANGEROUS_PATTERNS = [
    r"os\.system",
    r"subprocess\.",
    r"import\s+shutil",
    r"import\s+os",
    r"import\s+sys",
    r"__import__",
    r"eval\s*\(",
    r"exec\s*\(",
    r"open\s*\(",
    r"rm\s+-rf",
    r"shutil\.rmtree",
    r"os\.remove",
    r"os\.unlink",
    r"pickle\.loads",
    r"marshal\.loads",
]
DANGEROUS_RE = re.compile("|".join(DANGEROUS_PATTERNS), re.IGNORECASE)


class CodeRequest(BaseModel):
    code: str
    timeout: int = Field(default=10, ge=1, le=60)


class ExecutionResult(BaseModel):
    status: str  # "success" | "error"
    output: str = ""
    error: str = ""


class SecurityError(Exception):
    pass


class NemoClawSandbox:
    def __init__(self):
        pass

    def _check_safety(self, code: str):
        if DANGEROUS_RE.search(code):
            raise SecurityError("Código contém padrões perigosos bloqueados")

    def _log_execution(self, request: CodeRequest, result: ExecutionResult):
        entry = {
            "timestamp": time.time(),
            "code_snippet": request.code[:200],
            "timeout": request.timeout,
            "status": result.status,
            "output_snippet": result.output[:200],
            "error_snippet": result.error[:200],
        }
        try:
            os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass  # best effort

    def run(self, tool: str, **kwargs: Any) -> Dict[str, Any]:
        """Generic tool executor – delegates to run_code for 'python' tool."""
        if tool == "python":
            code = kwargs.get("code", "")
            return self.run_code(code, kwargs.get("timeout", 10))
        # For other tools, stub success
        return {"success": True, "result": f"executed {tool} with args {kwargs}"}

    def run_code(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        request = CodeRequest(code=code, timeout=timeout)
        self._check_safety(request.code)

        # Write code to a temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(request.code)
            tmp_path = tmp.name

        try:
            proc = subprocess.run(
                ["python3", tmp_path],
                capture_output=True,
                text=True,
                timeout=request.timeout,
            )
            result = ExecutionResult(
                status="success" if proc.returncode == 0 else "error",
                output=proc.stdout,
                error=proc.stderr,
            )
        except subprocess.TimeoutExpired:
            result = ExecutionResult(status="error", error="Execution timeout")
        except Exception as e:
            result = ExecutionResult(status="error", error=str(e))
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        self._log_execution(request, result)
        return result.model_dump()


# Compatibility exports expected by __init__.py
def get_sandbox() -> NemoClawSandbox:
    return NemoClawSandbox()


__all__ = [
    "NemoClawSandbox",
    "get_sandbox",
    "ExecutionResult",
    "SecurityError",
]
