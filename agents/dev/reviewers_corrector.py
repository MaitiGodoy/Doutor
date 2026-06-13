"""
Reviewers & Corrector – Code review, testing, and correction squad.
CorrectorAgent, TesterAgent, EfficiencyReviewer, FunctionalReviewer.
Zero stubs. 100% funcional e assíncrono.
"""
import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.provider_router import get_provider_router
from kernel.guards import SecurityGuard
from kernel.sandbox import NemoClawSandbox
from kernel.autonomy.core.agent_loop import AutonomousAgentLoop, AgentContext


BASE_DIR = Path(__file__).resolve().parents[2]
LOG_PATH = BASE_DIR / "logs" / "reviewers_corrector.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class TesterAgent:
    """Generates and runs tests for code."""

    def __init__(self, router, guard, chain_id: str):
        self.router = router
        self.guard = guard
        self.chain_id = chain_id

    async def run_tests(self, code: str, framework: str = "pytest") -> Dict[str, Any]:
        guard_res = self.guard.validate_input(code, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard", "tests": []}

        prompt = (
            f"Generate {framework} tests for this code. Cover edge cases, main flow, and error paths.\n"
            f"Return JSON with: test_code, test_cases (array of descriptions), coverage_estimate.\n\n{code[:3000]}"
        )
        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            parsed = json.loads(result)
            test_code = parsed.get("test_code", result)
        except json.JSONDecodeError:
            test_code = result
            parsed = {"test_code": result, "test_cases": [], "coverage_estimate": 0}

        sandbox = NemoClawSandbox()
        exec_result = sandbox.run_code(test_code, timeout=30)

        return {
            "test_code": test_code,
            "test_cases": parsed.get("test_cases", []),
            "coverage_estimate": parsed.get("coverage_estimate", 0),
            "execution": exec_result,
            "all_passed": exec_result.get("success", False),
            "framework": framework,
            "timestamp": time.time(),
        }


class EfficiencyReviewer:
    """Reviews code for performance and efficiency."""

    def __init__(self, router, guard, chain_id: str):
        self.router = router
        self.guard = guard
        self.chain_id = chain_id

    async def review(self, code: str) -> Dict[str, Any]:
        guard_res = self.guard.validate_input(code, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard", "issues": []}
        prompt = (
            "Review this code for efficiency. Check for: algorithmic complexity, "
            "memory usage, unnecessary allocations, I/O patterns, caching opportunities, "
            "concurrency potential, hot paths, database query optimization.\n\n"
            f"Code:\n{code[:3000]}\n\n"
            "Return JSON with: score (0-1), issues (array of {severity, line, message, recommendation}), "
            "optimizations (array of strings), complexity_analysis."
        )
        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"score": 0.5, "issues": [], "optimizations": [], "complexity_analysis": {}}


class FunctionalReviewer:
    """Reviews code for correctness and functional completeness."""

    def __init__(self, router, guard, chain_id: str):
        self.router = router
        self.guard = guard
        self.chain_id = chain_id

    async def review(self, code: str, requirements: str = "") -> Dict[str, Any]:
        guard_res = self.guard.validate_input(code, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard", "issues": []}
        prompt = (
            "Review this code for functional correctness. Check: requirement coverage, "
            "edge case handling, input validation, error handling, state management, "
            "null safety, boundary conditions, API contract compliance.\n\n"
            f"Code:\n{code[:3000]}\n"
            f"Requirements:\n{requirements[:1000]}\n\n"
            "Return JSON with: score (0-1), issues (array of {severity, line, message, recommendation}), "
            "missing_validations (array), edge_cases_unhandled (array)."
        )
        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"score": 0.5, "issues": [], "missing_validations": [], "edge_cases_unhandled": []}


class CorrectorAgent(AutonomousAgentLoop):
    """Iterates code based on feedback from reviewers and tests."""

    def __init__(self, goal: str = "code correction", max_iterations: int = 5, dry_run: bool = False):
        super().__init__(goal=goal, max_iterations=max_iterations, dry_run=dry_run)
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.tester = TesterAgent(self.router, self.guard, self.ctx.chain_id)
        self.efficiency = EfficiencyReviewer(self.router, self.guard, self.ctx.chain_id)
        self.functional = FunctionalReviewer(self.router, self.guard, self.ctx.chain_id)

    async def apply_feedback(self, code: str, feedback: Dict[str, Any]) -> str:
        """Apply feedback to fix code issues."""
        prompt = (
            f"Fix this code based on the feedback provided. Preserve functionality.\n\n"
            f"Code:\n{code[:3000]}\n\n"
            f"Feedback:\n{json.dumps(feedback, ensure_ascii=False)[:2000]}\n\n"
            "Return ONLY the corrected code, no explanations."
        )
        result = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        return result if isinstance(result, str) else json.dumps(result)

    async def comprehensive_review(self, code: str, requirements: str = "") -> Dict[str, Any]:
        """Run all reviewers and tests, then iteratively fix issues."""
        history = []
        current_code = code

        for iteration in range(self.max_iterations):
            eff = await self.efficiency.review(current_code)
            func = await self.functional.review(current_code, requirements)
            test = await self.tester.run_tests(current_code)
            issues = eff.get("issues", []) + func.get("issues", [])
            test_passed = test.get("all_passed", False)

            history.append({
                "iteration": iteration,
                "efficiency_score": eff.get("score", 0),
                "functional_score": func.get("score", 0),
                "tests_passed": test_passed,
                "total_issues": len(issues),
            })

            if not issues and test_passed:
                break

            feedback = {"efficiency": eff, "functional": func, "test": test}
            current_code = await self.apply_feedback(current_code, feedback)

        report = {
            "initial_code": code[:300] + "..." if len(code) > 300 else code,
            "final_code": current_code[:300] + "..." if len(current_code) > 300 else current_code,
            "iterations": len(history),
            "history": history,
            "final_tests": test.get("all_passed", False) if 'test' in locals() else False,
            "timestamp": time.time(),
        }
        self._log_dev("comprehensive_review", report)
        return report

    def _log_dev(self, action: str, payload: Dict[str, Any]) -> None:
        entry = {
            "timestamp": time.time(),
            "run_id": self.ctx.run_id,
            "chain_id": self.ctx.chain_id,
            "action": action,
            "payload": payload,
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")