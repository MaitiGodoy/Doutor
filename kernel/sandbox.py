import asyncio
import subprocess
import tempfile
import os
import json
import uuid
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

class SecurityError(Exception):
    pass

@dataclass
class ExecutionResult:
    status: str
    output: str
    error: Optional[str]
    execution_time: float
    execution_id: str

class NemoClawSandbox:
    def __init__(self, timeout: int = 15, max_memory_mb: int = 256):
        self.timeout = timeout
        self.max_memory_mb = max_memory_mb
        self.audit_log: List[Dict] = []
        
        # PadrÃµes perigosos (Blacklist)
        self._dangerous_patterns = [
            r'\b__import__\b', r'\beval\s*\(', r'\bexec\s*\(', r'\bcompile\s*\(',
            r'\bos\.(system|popen|spawn|fork)', r'\bsubprocess\b', 
            r'\bimport\s+(os|sys|shutil|ctypes|socket)\b',
            r'\bopen\s*\(' 
        ]

    async def execute_python(self, code: str, input_data: Optional[Dict] = None) -> ExecutionResult:
        exec_id = str(uuid.uuid4())
        start_time = asyncio.get_event_loop().time()

        try:
            # 1. ValidaÃ§Ã£o de SeguranÃ§a
            self._security_scan(code)
            
            # 2. Wrapping seguro
            wrapped_code = self._wrap_code(code, input_data)

            # 3. ExecuÃ§Ã£o em ambiente temporÃ¡rio
            with tempfile.TemporaryDirectory() as tmpdir:
                script_path = os.path.join(tmpdir, f"sandbox_{exec_id}.py")
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(wrapped_code)

                # 4. Processo isolado
                proc = await asyncio.create_subprocess_exec(
                    'python', script_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=tmpdir
                )

                try:
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
                    exec_time = asyncio.get_event_loop().time() - start_time

                    # Log de sucesso
                    self._log_execution(exec_id, code, "success", exec_time)

                    return ExecutionResult(
                        status="success" if proc.returncode == 0 else "error",
                        output=stdout.decode('utf-8', errors='replace').strip(),
                        error=stderr.decode('utf-8', errors='replace').strip() if stderr else None,
                        execution_time=exec_time,
                        execution_id=exec_id
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    await proc.wait()
                    return ExecutionResult(
                        status="timeout",
                        output="",
                        error=f"Execution exceeded limit of {self.timeout}s",
                        execution_time=float(self.timeout),
                        execution_id=exec_id
                    )

        except SecurityError as e:
            self._log_execution(exec_id, code, "blocked", 0.0, str(e))
            return ExecutionResult(status="blocked", output="", error=f"Security Violation: {e}", execution_time=0.0, execution_id=exec_id)
        except Exception as e:
            self._log_execution(exec_id, code, "crash", 0.0, str(e))
            return ExecutionResult(status="crash", output="", error=f"Sandbox Error: {str(e)}", execution_time=0.0, execution_id=exec_id)

    def _security_scan(self, code: str):
        for pattern in self._dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                raise SecurityError(f"Detected dangerous pattern: {pattern}")

    def _wrap_code(self, code: str, input_data: Optional[Dict] = None) -> str:
        # Isola o input e previne acesso ao escopo global
        input_json = json.dumps(input_data) if input_data else "None"
        return f'''
import sys
import json

# InjeÃ§Ã£o Segura de Dados
INPUT_DATA = {input_json}

def __sandbox_entry_point__():
    try:
{chr(10).join('        ' + line for line in code.splitlines())}
    except Exception as e:
        print(f"USER_CODE_ERROR: {{e}}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    __sandbox_entry_point__()
'''

    def _log_execution(self, exec_id: str, code: str, status: str, time: float, error: str = ""):
        self.audit_log.append({
            "id": exec_id,
            "status": status,
            "duration": time,
            "error_snippet": error[:50] if error else ""
        })
        if len(self.audit_log) > 5000:
            self.audit_log = self.audit_log[-5000:]

_sandbox_instance = None
def get_sandbox() -> NemoClawSandbox:
    global _sandbox_instance
    if _sandbox_instance is None:
        _sandbox_instance = NemoClawSandbox()
    return _sandbox_instance