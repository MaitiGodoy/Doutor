import difflib
import json
import os

class ScopeGuardian:
    def __init__(self):
        self.violations = []

    def validate_change(self, user_command: str, target_path: str, original_content: str, new_content: str) -> dict:
        """
        Valida se as mudanças estão estritamente dentro do escopo.
        """
        diff = list(difflib.unified_diff(
            original_content.splitlines(), 
            new_content.splitlines(), 
            lineterm=''
        ))
        
        violations = []
        if len(diff) > 0:
            if self._is_formatting_only_change(original_content, new_content):
                 if not self._is_target_small_scope(user_command):
                     violations.append("Global formatting change detected when local change was requested.")

        if violations:
            return {
                "status": "blocked",
                "violations": violations,
                "message": f"Scope Violation: Changes detected outside the requested target. Please restrict changes to: {user_command}"
            }
        
        return {"status": "approved", "message": "Scope validated."}

    def _is_formatting_only_change(self, orig: str, new: str) -> bool:
        return orig.replace(" ", "").replace("\n", "") == new.replace(" ", "").replace("\n", "")

    def _is_target_small_scope(self, command: str) -> bool:
        small_keywords = ["linha", "função", "método", "classe", "parágrafo", "botão", "título"]
        return any(k in command.lower() for k in small_keywords)

async def execute_with_guardian(executor_output: dict, target_path: str, original_content: str, user_command: str) -> dict:
    guardian = ScopeGuardian()
    validation = guardian.validate_change(user_command, target_path, original_content, executor_output['content'])
    
    if validation['status'] == 'blocked':
        print(f"[GUARDIAN] BLOCKED: {validation['message']}")
        return {
            "status": "retry",
            "error": validation['message'],
            "instruction": f"STRICT SCOPE ERROR: You modified files/sections not requested. Re-generate output changing ONLY what was asked in: '{user_command}'. Do not touch anything else."
        }
    
    # Save file
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(executor_output['content'])
    return {"status": "success"}
