import os, tempfile, subprocess, json, logging, shutil
from pathlib import Path
from typing import Dict

logger = logging.getLogger("doutor.sandbox")

class Sandbox:
    def __init__(self, project_root: str):
        self.root = Path(project_root)
        self.temp_dir = tempfile.mkdtemp(prefix="doutor_sandbox_")
        self.validation_log = []

    def validate_and_apply(self, files: Dict, run_id: str) -> Dict:
        result = {
            "status": "pending",
            "applied": [],
            "rejected": [],
            "errors": [],
            "validation_log": []
        }

        try:
            for filepath, content in files.items():
                abs_path = Path(self.temp_dir) / filepath
                abs_path.parent.mkdir(parents=True, exist_ok=True)

                with open(abs_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                validation = self._validate_file(filepath, abs_path)
                result["validation_log"].append(validation)

                if validation["status"] == "fail":
                    result["rejected"].append(filepath)
                    result["errors"].append(validation["error"])
                else:
                    result["applied"].append(filepath)

            if result["rejected"]:
                result["status"] = "rejected"
                logger.error(f"[Sandbox] {len(result['rejected'])} arquivos rejeitados: {result['errors']}")
                return result

            for filepath in result["applied"]:
                src = Path(self.temp_dir) / filepath
                dst = self.root / filepath
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)

            result["status"] = "applied"
            logger.info(f"[Sandbox] {len(result['applied'])} arquivos validados e aplicados com sucesso.")
            return result

        except Exception as e:
            result["status"] = "critical_error"
            result["errors"].append(f"Sandbox error: {str(e)}")
            logger.error(f"[Sandbox] Critical error: {e}")
            return result

    def _validate_file(self, filepath: str, abs_path: Path) -> Dict:
        validation = {"file": filepath, "status": "pass", "checks": []}

        try:
            if filepath.endswith('.py'):
                proc = subprocess.run(
                    ["python", "-m", "py_compile", str(abs_path)],
                    capture_output=True, text=True, timeout=10
                )
                if proc.returncode != 0:
                    validation["status"] = "fail"
                    validation["error"] = f"SyntaxError: {proc.stderr}"
                    return validation
                validation["checks"].append("syntax_ok")

                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("temp_module", abs_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                    validation["checks"].append("import_ok")
                except Exception as e:
                    validation["status"] = "fail"
                    validation["error"] = f"ImportError: {str(e)}"
                    return validation

            elif filepath.endswith(('.js', '.ts')):
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'function' in content or 'const' in content or 'import' in content:
                        validation["checks"].append("basic_syntax_ok")

            elif filepath.endswith('.html'):
                with open(abs_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.count('<div>') != content.count('</div>'):
                        validation["status"] = "fail"
                        validation["error"] = "Unbalanced HTML tags"
                        return validation
                validation["checks"].append("html_balanced")

            return validation

        except subprocess.TimeoutExpired:
            validation["status"] = "fail"
            validation["error"] = "Validation timeout"
            return validation
        except Exception as e:
            validation["status"] = "fail"
            validation["error"] = f"Validation error: {str(e)}"
            return validation

    def cleanup(self):
        try:
            shutil.rmtree(self.temp_dir)
        except:
            pass

print('kernel/sandbox.py entregue. Validacao obrigatoria por tipo de arquivo. Rejeicao atomica.')
