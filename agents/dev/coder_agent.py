"""
CoderAgent – Autonomous code generation agent.
Inherits from AutonomousAgentLoop. Implements ReAct+Reflexion cycle for code generation.
Uses provider_router for model selection, sandbox for execution/testing.
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
LOG_PATH = BASE_DIR / "logs" / "coder_agent.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class CoderAgent(AutonomousAgentLoop):
    """Autonomous code generation agent with ReAct+Reflexion cycle."""

    def __init__(
        self,
        goal: str = "code generation",
        max_iterations: int = 5,
        dry_run: bool = False,
        language: str = "python",
    ):
        super().__init__(goal=goal, max_iterations=max_iterations, dry_run=dry_run)
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.sandbox = NemoClawSandbox()
        self.language = language
        self.generated_files: Dict[str, str] = {}

    async def propose(self, code_spec: str) -> Dict[str, Any]:
        """
        Generate code from specification using ReAct+Reflexion cycle.
        Returns dict with code, tests, and execution results.
        """
        # Perceive: understand the specification
        perception = await self._perceive_spec(code_spec)
        
        # Plan: create implementation plan
        plan = await self._plan_implementation(perception)
        
        # Act: generate code
        code_result = await self._generate_code(plan)
        
        # Reflect: test and iterate
        final_result = await self._reflect_and_iterate(code_result, plan)
        
        self._log_coder("propose", final_result)
        return final_result

    async def _perceive_spec(self, code_spec: str) -> Dict[str, Any]:
        """Analyze the code specification."""
        prompt = (
            f"Analyze this code specification and extract key requirements:\n\n"
            f"{code_spec}\n\n"
            "Return JSON with: language, functions_needed, classes_needed, "
            "dependencies, input_types, output_types, constraints, test_cases."
        )
        guard_res = self.guard.validate_input(code_spec, context={"chain_id": self.ctx.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard"}

        result = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw": result, "language": self.language}

    async def _plan_implementation(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        """Create implementation plan from perception."""
        prompt = (
            f"Create a detailed implementation plan for this code specification:\n\n"
            f"{json.dumps(perception, ensure_ascii=False)}\n\n"
            f"Language: {self.language}\n"
            "Return JSON with: file_structure, function_signatures, class_definitions, "
            "implementation_order, test_strategy, edge_cases."
        )
        result = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw": result}

    async def _generate_code(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Generate code files from plan."""
        prompt = (
            f"Implement the code based on this plan:\n\n"
            f"{json.dumps(plan, ensure_ascii=False)[:3000]}\n\n"
            f"Language: {self.language}\n"
            "Generate complete, production-ready code with proper error handling, "
            "type hints, docstrings, and modular structure. "
            "Return JSON with files: {filename: code_content}."
        )
        result = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            files = json.loads(result)
            self.generated_files = files
        except json.JSONDecodeError:
            files = {"main.py": result}
            self.generated_files = files

        return {"files": files, "plan": plan}

    async def _reflect_and_iterate(self, code_result: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
        """Test code in sandbox, reflect, and iterate if needed."""
        files = code_result.get("files", {})
        test_results = []
        
        for iteration in range(self.max_iterations):
            # Write files to sandbox and test
            for filename, content in files.items():
                if filename.endswith(".py"):
                    # Create test file
                    test_prompt = (
                        f"Generate pytest tests for this code:\n\n{content}\n\n"
                        "Return only the test code as a string."
                    )
                    test_code = await self.router.route(test_prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
                    
                    # Run tests in sandbox
                    sandbox_result = self.sandbox.run_code(test_code, timeout=30)
                    test_results.append({
                        "file": filename,
                        "iteration": iteration,
                        "success": sandbox_result.get("success", False),
                        "output": sandbox_result.get("output", ""),
                        "error": sandbox_result.get("error", ""),
                    })
                    
                    if sandbox_result.get("success"):
                        break
            
            # Check if all tests pass
            all_passed = all(r.get("success", False) for r in test_results if r.get("iteration") == iteration)
            
            if all_passed:
                break
            
            # Reflect: analyze failures and iterate
            reflection = await self._reflect_on_failures(files, test_results[-1], plan)
            files = reflection.get("files", files)
            self.generated_files = files
        
        return {
            "files": self.generated_files,
            "test_results": test_results,
            "iterations": iteration + 1,
            "final_success": all(r.get("success", False) for r in test_results[-len(files):]) if test_results else False,
            "timestamp": time.time(),
        }

    async def _reflect_on_failures(
        self, 
        files: Dict[str, str], 
        last_test: Dict[str, Any], 
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Reflect on test failures and generate fixes."""
        prompt = (
            f"Code failed tests. Analyze and fix:\n\n"
            f"Files: {json.dumps(files, ensure_ascii=False)[:3000]}\n\n"
            f"Last test error: {last_test.get('error', '')}\n"
            f"Last test output: {last_test.get('output', '')}\n\n"
            f"Original plan: {json.dumps(plan, ensure_ascii=False)[:1000]}\n\n"
            "Return JSON with fixed files: {filename: fixed_code}."
        )
        result = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"files": files}

    async def generate_with_context(
        self,
        spec: str,
        existing_files: Dict[str, str],
    ) -> Dict[str, Any]:
        """Generate code that integrates with existing codebase."""
        context_prompt = (
            f"Generate code for this spec that integrates with existing files:\n\n"
            f"Spec: {spec}\n\n"
            f"Existing files: {json.dumps(existing_files, ensure_ascii=False)[:2000]}\n\n"
            "Return JSON with new/updated files."
        )
        result = await self.router.route(context_prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"raw": result}

    def _log_coder(self, action: str, payload: Dict[str, Any]) -> None:
        entry = {
            "timestamp": time.time(),
            "run_id": self.ctx.run_id,
            "chain_id": self.ctx.chain_id,
            "action": action,
            "language": self.language,
            "payload": payload,
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")