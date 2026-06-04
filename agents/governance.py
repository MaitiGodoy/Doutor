import os
import json
import difflib
from pathlib import Path
from typing import Dict, List, Any, Optional
from agents.base_agent import BaseAgent


class ConstitutionAgent(BaseAgent):
    def __init__(self, config: Dict = None, router=None):
        super().__init__("the_constitution", config or {}, router)
        self.master_template_path = Path("templates/architecture_master.json")

    async def validate(self, plan: Dict, context: Dict = None) -> Dict:
        violations = []
        plan_json = json.dumps(plan, default=str).lower()
        context = context or {}

        if self.master_template_path.exists():
            try:
                template = json.loads(self.master_template_path.read_text(encoding="utf-8"))
                for phase in template.get("required_phases", []):
                    if phase not in plan:
                        violations.append({"type": "missing_required_phase", "detail": f"Fase '{phase}' ausente", "severity": "medium", "standard": "ARCHITECTURE_MASTER"})
            except Exception:
                pass

        required_keys = ["module", "approach", "deliverables", "timeline"]
        for key in required_keys:
            if key not in plan:
                violations.append({
                    "type": "missing_required_key",
                    "detail": f"Plano não contém '{key}'",
                    "severity": "high",
                    "standard": "INTERNAL",
                })

        if "deliverables" in plan and isinstance(plan["deliverables"], list):
            if len(plan["deliverables"]) == 0:
                violations.append({
                    "type": "empty_deliverables",
                    "detail": "Plano não define deliverables",
                    "severity": "high",
                    "standard": "INTERNAL",
                })

        blocked_terms = ["rm -rf /", "drop table", "truncate", "shutdown", "format"]
        for term in blocked_terms:
            if term in plan_json:
                violations.append({
                    "type": "blocked_operation",
                    "detail": f"Plano contém operação bloqueada: {term}",
                    "severity": "critical",
                    "standard": "INTERNAL",
                })

        result = {
            "mode": "constitution_validation",
            "plan_summary": str(plan)[:300],
            "approved": len([v for v in violations if v["severity"] in ("critical", "high")]) == 0,
            "violations": violations,
            "violation_count": len(violations),
            "requires_resubmission": any(v["severity"] == "critical" for v in violations),
        }
        self._log_execution({"mode": "constitution_validate", "result": result})
        return result


class SurgeonAgent(BaseAgent):
    def __init__(self, config: Dict = None, router=None):
        super().__init__("the_surgeon", config or {}, router)

    async def validate_change(self, user_command: str, target_path: str, original_content: str, new_content: str) -> Dict:
        violations = []
        original_lines = original_content.split("\n")
        new_lines = new_content.split("\n")

        diff = list(difflib.unified_diff(
            original_lines, new_lines,
            fromfile=f"a/{target_path}", tofile=f"b/{target_path}",
            lineterm=""
        ))

        added = [l[1:] for l in diff if l.startswith("+") and not l.startswith("+++")]
        removed = [l[1:] for l in diff if l.startswith("-") and not l.startswith("---")]

        command_lower = user_command.lower()
        for line in added:
            stripped = line.strip().lower()
            if "import " in stripped and stripped not in command_lower:
                violations.append({
                    "type": "unauthorized_import",
                    "detail": f"Importação não solicitada: {line.strip()}",
                    "severity": "medium",
                    "line_content": line.strip(),
                })
            if "os.system" in stripped or "subprocess.call" in stripped:
                if "exec" not in command_lower and "shell" not in command_lower:
                    violations.append({
                        "type": "unauthorized_exec",
                        "detail": f"Execução não autorizada: {line.strip()}",
                        "severity": "high",
                        "line_content": line.strip(),
                    })

        for line in removed:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                for kw in ["api", "key", "token", "secret", "password"]:
                    if kw in stripped.lower() and ("remove" not in command_lower and "delete" not in command_lower):
                        violations.append({
                            "type": "unauthorized_removal",
                            "detail": f"Linha removida potencialmente sensível: {stripped[:100]}",
                            "severity": "high",
                            "line_content": stripped[:100],
                        })

        result = {
            "mode": "surgeon_diff_validation",
            "user_command": user_command[:200],
            "target_path": target_path,
            "approved": len([v for v in violations if v["severity"] == "high"]) == 0,
            "unauthorized_changes": violations,
            "lines_added": len(added),
            "lines_removed": len(removed),
            "diff_lines": len(diff),
        }
        self._log_execution({"mode": "surgeon_validate", "result": result})
        return result
