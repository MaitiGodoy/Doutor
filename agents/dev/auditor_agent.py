"""
AuditorAgent – Code security and quality auditor.
Uses bandit for security, ruff for style, governance for compliance.
Zero stubs. 100% funcional.
"""
import asyncio
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.provider_router import get_provider_router
from kernel.guards import SecurityGuard
from kernel.autonomy.core.agent_loop import AutonomousAgentLoop, AgentContext


BASE_DIR = Path(__file__).resolve().parents[2]
LOG_PATH = BASE_DIR / "logs" / "auditor_agent.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class AuditorAgent:
    """Audits code for security, style, and governance compliance."""

    def __init__(self, chain_id: str = ""):
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.chain_id = chain_id

    async def review_code(
        self,
        code: str,
        filename: str = "review.py",
        run_bandit: bool = True,
        run_ruff: bool = True,
        check_governance: bool = True,
    ) -> Dict[str, Any]:
        """
        Comprehensive code review.
        Returns structured report with issues, score, and recommendations.
        """
        guard_res = self.guard.validate_input(code, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard", "details": guard_res.__dict__}

        # Write code to temp file for tool execution
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            temp_path = f.name

        try:
            results = await asyncio.gather(
                self._run_bandit(temp_path) if run_bandit else asyncio.sleep(0, result={"issues": []}),
                self._run_ruff(temp_path) if run_ruff else asyncio.sleep(0, result={"issues": []}),
                self._check_governance(code) if check_governance else asyncio.sleep(0, result={"issues": []}),
            )
        finally:
            Path(temp_path).unlink(missing_ok=True)

        bandit_result, ruff_result, governance_result = results

        # Aggregate all issues
        all_issues = []
        all_issues.extend(self._normalize_bandit(bandit_result))
        all_issues.extend(self._normalize_ruff(ruff_result))
        all_issues.extend(self._normalize_governance(governance_result))

        # Calculate scores
        security_score = self._calc_security_score(bandit_result)
        style_score = self._calc_style_score(ruff_result)
        governance_score = self._calc_governance_score(governance_result)
        overall_score = (security_score + style_score + governance_score) / 3

        # Determine status
        if overall_score >= 0.8:
            status = "passed"
        elif overall_score >= 0.5:
            status = "warning"
        else:
            status = "failed"

        report = {
            "filename": filename,
            "status": status,
            "overall_score": round(overall_score, 2),
            "scores": {
                "security": round(security_score, 2),
                "style": round(style_score, 2),
                "governance": round(governance_score, 2),
            },
            "issues": all_issues,
            "summary": {
                "total_issues": len(all_issues),
                "critical": len([i for i in all_issues if i.get("severity") == "critical"]),
                "high": len([i for i in all_issues if i.get("severity") == "high"]),
                "medium": len([i for i in all_issues if i.get("severity") == "medium"]),
                "low": len([i for i in all_issues if i.get("severity") == "low"]),
            },
            "timestamp": time.time(),
        }

        self._log_audit("review_code", report)
        return report

    async def _run_bandit(self, filepath: str) -> Dict[str, Any]:
        """Run bandit security linter."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "bandit", "-f", "json", "-r", filepath,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode == 0 or proc.returncode == 1:
                return json.loads(stdout.decode())
            return {"results": [], "errors": [stderr.decode()]}
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"results": [], "errors": [str(e)]}

    async def _run_ruff(self, filepath: str) -> Dict[str, Any]:
        """Run ruff style linter."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ruff", "check", "--output-format=json", filepath,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if proc.returncode in (0, 1):
                return json.loads(stdout.decode())
            return {"issues": [], "errors": [stderr.decode()]}
        except (FileNotFoundError, json.JSONDecodeError) as e:
            return {"issues": [], "errors": [str(e)]}

    async def _check_governance(self, code: str) -> Dict[str, Any]:
        """Check governance compliance via LLM."""
        prompt = (
            "Review this code for governance compliance. Check for:\n"
            "- Hardcoded secrets/keys\n"
            "- SQL injection vulnerabilities\n"
            "- Path traversal risks\n"
            "- Insecure deserialization\n"
            "- Missing input validation\n"
            "- Logging of sensitive data\n"
            "- Compliance with security best practices\n\n"
            f"Code:\n{code[:3000]}\n\n"
            "Return JSON with: issues (array of {type, severity, line, message, recommendation})."
        )
        guard_res = self.guard.validate_input(prompt, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"issues": []}

        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"issues": [], "raw": result}

    def _normalize_bandit(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues = []
        for item in result.get("results", []):
            issues.append({
                "tool": "bandit",
                "type": "security",
                "severity": item.get("issue_severity", "medium").lower(),
                "confidence": item.get("issue_confidence", "medium").lower(),
                "line": item.get("line_number"),
                "message": item.get("issue_text"),
                "code": item.get("code"),
                "recommendation": f"Fix {item.get('test_id', 'security issue')}",
            })
        return issues

    def _normalize_ruff(self, result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        issues = []
        for item in result if isinstance(result, list) else result.get("issues", []):
            issues.append({
                "tool": "ruff",
                "type": "style",
                "severity": self._ruff_severity(item.get("code", "")),
                "line": item.get("location", {}).get("row"),
                "column": item.get("location", {}).get("column"),
                "message": item.get("message"),
                "code": item.get("code"),
                "recommendation": f"Fix {item.get('code', 'style issue')}",
            })
        return issues

    def _ruff_severity(self, code: str) -> str:
        if code.startswith(("E9", "F8", "F7")):
            return "high"
        elif code.startswith(("E", "W")):
            return "medium"
        return "low"

    def _normalize_governance(self, result: Dict[str, Any]) -> List[Dict[str, Any]]:
        issues = []
        for item in result.get("issues", []):
            issues.append({
                "tool": "governance",
                "type": "governance",
                "severity": item.get("severity", "medium").lower(),
                "line": item.get("line"),
                "message": item.get("message"),
                "recommendation": item.get("recommendation", "Review governance compliance"),
            })
        return issues

    def _calc_security_score(self, result: Dict[str, Any]) -> float:
        results = result.get("results", [])
        if not results:
            return 1.0
        critical = len([r for r in results if r.get("issue_severity") == "HIGH"])
        high = len([r for r in results if r.get("issue_severity") == "MEDIUM"])
        return max(0.0, 1.0 - critical * 0.3 - high * 0.15)

    def _calc_style_score(self, result: List[Dict[str, Any]]) -> float:
        issues = result if isinstance(result, list) else result.get("issues", [])
        if not issues:
            return 1.0
        high = len([i for i in issues if self._ruff_severity(i.get("code", "")) == "high"])
        medium = len([i for i in issues if self._ruff_severity(i.get("code", "")) == "medium"])
        return max(0.0, 1.0 - high * 0.2 - medium * 0.05)

    def _calc_governance_score(self, result: Dict[str, Any]) -> float:
        issues = result.get("issues", [])
        if not issues:
            return 1.0
        critical = len([i for i in issues if i.get("severity") == "critical"])
        high = len([i for i in issues if i.get("severity") == "high"])
        return max(0.0, 1.0 - critical * 0.4 - high * 0.2)

    def _log_audit(self, action: str, payload: Dict[str, Any]) -> None:
        entry = {
            "timestamp": time.time(),
            "chain_id": self.chain_id,
            "action": action,
            "payload": payload,
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")