import os, json, time, asyncio, logging
from pathlib import Path
from typing import Dict, Optional
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.omni_aa")

class OmniAaAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_omni_aa", config, router)
        self.dry_run = config.get("safety", {}).get("dry_run_mandatory", True)
        self.timeout = config.get("safety", {}).get("timeout_sec", 30)
        self.log_path = Path(config.get("log_path", "logs/omni_aa.jsonl"))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    async def execute_infra_task(self, command: str, target: str = "", dry_run_override: bool = False) -> Dict:
        if not dry_run_override and self.dry_run:
            cmd = f"echo '[DRY-RUN] {command}' && ({command} --dry-run 2>&1 || true)"
            log_mode = "dry_run"
        else:
            cmd = command
            log_mode = "production"

        start = time.time()
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)

            result = {
                "status": "success" if proc.returncode == 0 else "fail",
                "target": target,
                "command_preview": command[:200],
                "stdout": stdout.decode(errors="replace")[:1000],
                "stderr": stderr.decode(errors="replace")[:500],
                "return_code": proc.returncode,
                "execution_mode": log_mode,
                "execution_time_ms": int((time.time() - start) * 1000)
            }
            self._log(result)
            return result
        except asyncio.TimeoutError:
            err = {"status": "fail", "error": "timeout", "target": target, "execution_mode": log_mode, "execution_time_ms": self.timeout * 1000}
            self._log(err)
            return err
        except Exception as e:
            err = {"status": "fail", "error": str(e), "target": target}
            self._log(err)
            return err

    async def handle_2fa_prompt(self, provider: str, method: str) -> Dict:
        return {"status": "awaiting_2fa", "provider": provider, "method": method, "instruction": f"Insira o código 2FA para {provider} ({method}). Aguardando input do usuário.", "state_saved": True}

    def _log(self, data: Dict):
        entry = {"timestamp": time.time(), "status": data.get("status"), "target": data.get("target"), "mode": data.get("execution_mode"), "error": data.get("error")}
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

# EOF
