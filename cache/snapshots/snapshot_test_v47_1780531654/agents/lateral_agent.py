import os, json, subprocess, time
from pathlib import Path
from typing import Dict, List, Any
from kernel.lateral_agent import LateralAgent as _LateralAgent

class LateralAgent(_LateralAgent):
    async def validate_alternative_compliance(self, alternative: Dict) -> Dict:
        findings = []
        target = alternative.get("target", ".")
        target_abs = self._resolve_target(target)

        findings += self._scan_secrets(target_abs)
        findings += self._scan_cors_headers(target_abs)
        findings += self._scan_cookies(target_abs)
        findings += self._scan_debug_flags(target_abs)
        findings += self._scan_dep_lock(target_abs)

        try:
            bandit = subprocess.run(["bandit", "-r", str(target_abs), "-f", "json", "-ll"], capture_output=True, text=True, timeout=30)
            if bandit.stdout:
                data = json.loads(bandit.stdout)
                for issue in data.get("results", []):
                    findings.append({
                        "type": issue.get("test_id", "unknown"),
                        "severity": issue.get("issue_severity", "medium").lower(),
                        "standard": "OWASP",
                        "location": {"file": issue.get("filename"), "line": issue.get("line_number"), "package": None},
                        "description": issue.get("issue_text", ""),
                        "remediation": "Revisar padrão de código seguro conforme OWASP",
                        "auto_fix_available": False,
                        "patch_hint": ""
                    })
        except Exception:
            pass

        try:
            req_file = target_abs / "requirements.txt" if target_abs.is_dir() else target_abs
            if req_file.exists():
                safety = subprocess.run(["safety", "check", "-r", str(req_file.resolve()), "--json"], capture_output=True, text=True, timeout=30)
                if safety.stdout:
                    vulns = json.loads(safety.stdout)
                    vuln_list = vulns if isinstance(vulns, list) else vulns.get("vulnerabilities", [])
                    for v in vuln_list:
                        findings.append({
                            "type": "vulnerable_dependency",
                            "severity": "high" if v.get("severity") == "CRITICAL" else "medium",
                            "standard": "CVE",
                            "location": {"file": None, "line": None, "package": v.get("package_name")},
                            "description": v.get("description", ""),
                            "remediation": f"Atualizar para {v.get('fixed_version', 'latest')}",
                            "auto_fix_available": True,
                            "patch_hint": ""
                        })
        except Exception:
            pass

        total_risk = sum({"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.1}.get(f["severity"], 0.1) for f in findings)
        avg_risk = total_risk / max(len(findings), 1)

        result = {
            "alternative_name": alternative.get("name", "unknown"),
            "compliance_status": "approved" if avg_risk < 0.5 else "blocked",
            "findings_count": len(findings),
            "overall_risk_score": round(avg_risk, 2),
            "findings": findings,
            "requires_human_review": avg_risk >= 0.7,
        }

        self._log_audit({"mode": "validate_alternative_compliance", "findings": findings, "recommendation": result["compliance_status"]})
        return result
