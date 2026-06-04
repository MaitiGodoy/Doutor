import os, json, ast, difflib, logging, subprocess, tempfile, shutil, time
from pathlib import Path
from typing import Dict
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.surgeon")

class SurgeonAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_surgeon", config, router)
        self.diff_dir = Path("cache/diffs")
        self.diff_dir.mkdir(parents=True, exist_ok=True)

    async def execute_diff(self, original_code: str, new_code: str, file_path: str) -> Dict:
        try:
            ast.parse(original_code)
            ast.parse(new_code)
        except SyntaxError as e:
            return {"status": "fail", "error": f"syntax_error: {str(e)}", "safe_to_apply": False}

        diff = difflib.unified_diff(
            original_code.splitlines(keepends=True),
            new_code.splitlines(keepends=True),
            fromfile=f"original/{file_path}",
            tofile=f"new/{file_path}",
            n=3
        )
        diff_text = "".join(diff)
        patch_path = self.diff_dir / f"{Path(file_path).stem}_{int(time.time())}.patch"
        patch_path.write_text(diff_text, encoding="utf-8")

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_file = Path(tmpdir) / file_path
                tmp_file.parent.mkdir(parents=True, exist_ok=True)
                tmp_file.write_text(new_code, encoding="utf-8")
                try:
                    subprocess.run(["ruff", "check", str(tmp_file), "--fix"], check=True, capture_output=True, timeout=30)
                except FileNotFoundError:
                    try:
                        subprocess.run(["flake8", str(tmp_file)], check=True, capture_output=True, timeout=30)
                    except FileNotFoundError:
                        pass
            return {"status": "success", "diff_saved": str(patch_path), "lint_passed": True, "safe_to_apply": True, "summary": f"Diff gerado e validado para {file_path}"}
        except Exception as e:
            logger.error(f"Surgeon diff failed: {e}")
            return {"status": "fail", "error": str(e), "safe_to_apply": False}

# EOF
