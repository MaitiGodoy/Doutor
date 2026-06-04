import os, tempfile, subprocess, json, logging, shutil
from pathlib import Path

logger = logging.getLogger("doutor.sandbox")

class Sandbox:
    def __init__(self, project_root: str):
        self.root = project_root
        self.temp_dir = tempfile.mkdtemp(prefix="doutor_sandbox_")

    def validate_and_apply(self, files: dict, run_id: str) -> dict:
        result = {"status": "pending", "applied": [], "errors": []}

        try:
            for filepath, content in files.items():
                abs_path = os.path.join(self.temp_dir, filepath)
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                with open(abs_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                if filepath.endswith('.py'):
                    proc = subprocess.run(
                        ["python", "-m", "py_compile", abs_path],
                        capture_output=True, text=True
                    )
                    if proc.returncode != 0:
                        result["errors"].append(f"SyntaxError in {filepath}: {proc.stderr}")
                        continue

                elif filepath.endswith(('.js', '.ts')):
                    pass

                result["applied"].append(filepath)

            if not result["errors"]:
                for filepath in result["applied"]:
                    src = os.path.join(self.temp_dir, filepath)
                    dst = os.path.join(self.root, filepath)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                result["status"] = "success"
                logger.info(f"[Sandbox] {len(result['applied'])} arquivos validados e aplicados.")
            else:
                result["status"] = "failed"
                logger.error(f"[Sandbox] Falha na validacao: {result['errors']}")

        except Exception as e:
            result["status"] = "critical_error"
            result["errors"].append(str(e))

        return result
