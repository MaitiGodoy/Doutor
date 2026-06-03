from typing import Dict, Any
import asyncio

class BaseAgent:
    def __init__(self, role: str, config: Dict, router):
        self.role = role
        self.config = config
        self.router = router

    async def execute(self, prompt: str, force_chronic: bool = False) -> Dict[str, Any]:
        # This is a placeholder. In a real implementation, this would call the LLM.
        # For the purpose of this exercise, we return a dummy response.
        return {
            "response": {
                "content": "{}"
            }
        }

    async def execute_with_council_lens(self, task_context: Dict, forced_perspective: str) -> Dict:
        """Executa forçando o agente a aplicar sua perspectiva única."""
        prompt = f"""
Contexto: {json.dumps(task_context, default=str)[:500]}
Sua Perspectiva Forçada: {forced_perspective}

Aja conforme sua persona, mas foque estritamente em como isso afeta {forced_perspective}.
"""
        return await self.execute(prompt)