import os, ast, json, hashlib, logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger("doutor.warden")

class AntiEntropy:
    def __init__(self, project_root: str, baseline_path: str):
        self.root = Path(project_root)
        self.baseline_path = Path(baseline_path)
        self.baseline = self._load_baseline()
        self.violations = []

    def _load_baseline(self) -> Dict:
        if not self.baseline_path.exists():
            self.generate_baseline()
        with open(self.baseline_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def generate_baseline(self):
        baseline = {"prompts": {}, "code_structure": {}, "critical_methods": []}

        for p in self.root.glob("prompts/*.md"):
            content = p.read_text(encoding="utf-8")
            baseline["prompts"][p.name] = {
                "size": len(content),
                "lines": len(content.splitlines()),
                "hash": self._hash_file(p)
            }

        for py in sorted(self.root.glob("agents/*.py")):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            methods = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            key = f"agents/{py.name}"
            baseline["code_structure"][key] = methods
            for m in methods:
                if "execute" in m or "validate" in m:
                    baseline["critical_methods"].append(f"{key}:{m}")

        for py in sorted(self.root.glob("kernel/*.py")):
            tree = ast.parse(py.read_text(encoding="utf-8"))
            methods = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            key = f"kernel/{py.name}"
            baseline["code_structure"][key] = methods
            for m in methods:
                if "execute" in m or "validate" in m or "enforce" in m or "convene" in m:
                    baseline["critical_methods"].append(f"{key}:{m}")

        self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
        self.baseline_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        logger.info("[AntiEntropy] Baseline v4.7 gerado e travado.")

    def _scan_dir(self, subdir: str) -> List[Dict]:
        violations = []
        for py in sorted(self.root.glob(f"{subdir}/*.py")):
            content = py.read_text(encoding="utf-8")
            tree = ast.parse(content)
            key = f"{subdir}/{py.name}"

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    body = node.body
                    if len(body) == 1:
                        is_stub = False
                        if isinstance(body[0], ast.Pass):
                            is_stub = True
                        if isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                            val = str(body[0].value.value).lower()
                            if val in ("pass", "todo", "implement later"):
                                is_stub = True
                        if isinstance(body[0], ast.Raise):
                            call = body[0].exc
                            if isinstance(call, ast.Call) and hasattr(call.func, 'id') and 'NotImplemented' in call.func.id:
                                is_stub = True
                        if is_stub:
                            violations.append({
                                "type": "stub_method", "file": str(py),
                                "method": node.name, "severity": "critical"
                            })

            current_methods = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            expected = self.baseline["code_structure"].get(key, [])
            missing = [m for m in expected if m not in current_methods]
            if missing:
                violations.append({
                    "type": "missing_methods", "file": str(py),
                    "methods": missing, "severity": "critical"
                })

        return violations

    def scan_codebase(self) -> List[Dict]:
        return self._scan_dir("agents") + self._scan_dir("kernel")

    def scan_prompts(self) -> List[Dict]:
        violations = []
        for name, meta in self.baseline.get("prompts", {}).items():
            prompt_path = self.root / "prompts" / name
            if not prompt_path.exists():
                violations.append({
                    "type": "missing_prompt", "file": name, "severity": "critical"
                })
                continue

            content = prompt_path.read_text(encoding="utf-8")
            size_diff = len(content) - meta["size"]
            if size_diff < -meta["size"] * 0.1:
                violations.append({
                    "type": "prompt_degradation", "file": name,
                    "lost_chars": abs(size_diff), "severity": "high"
                })

        return violations

    def enforce(self) -> Dict:
        code_violations = self.scan_codebase()
        prompt_violations = self.scan_prompts()
        self.violations = code_violations + prompt_violations

        if any(v["severity"] == "critical" for v in self.violations):
            return {
                "status": "blocked",
                "reason": "degradation_detected",
                "violations": self.violations,
                "action": "restore_baseline_or_fix"
            }

        return {"status": "clean", "violations": self.violations}

    def _hash_file(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
