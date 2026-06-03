from typing import Dict, Any
import asyncio
import time
import json
from kernel.observability import observability

class BaseAgent:
    def __init__(self, role: str, config: Dict, router):
        self.role = role
        self.config = config
        self.router = router

    async def execute(self, prompt: str, force_chronic: bool = False) -> Dict[str, Any]:
        start_time = time.time()
        # Placeholder LLM call
        result = {
            "response": {
                "content": "{}"
            }
        }
        end_time = time.time()
        latency = (end_time - start_time) * 1000
        response_content = result.get("response", {}).get("content", "")
        tokens_estimated = len(prompt.split()) + len(response_content.split())
        
        # Trace to Langfuse if enabled
        if observability.enabled and observability.langfuse:
            try:
                observability.langfuse.trace(
                    name=f"{self.role}_execute",
                    input=prompt,
                    output=response_content,
                    metadata={
                        "agent": self.role,
                        "phase": "execute",
                        "latency_ms": latency,
                        "tokens_estimated": tokens_estimated
                    }
                )
            except Exception as e:
                print(f"[Observability] Failed to trace to Langfuse: {e}")
        
        return result

    async def execute_with_council_lens(self, task_context: Dict, forced_perspective: str) -> Dict:
        """Executa forçando o agente a aplicar sua perspectiva única."""
        prompt = f"""
Contexto: {json.dumps(task_context, default=str)[:500]}
Sua Perspectiva Forçada: {forced_perspective}

Aja conforme sua persona, mas foque estritamente em como isso afeta {forced_perspective}.
"""
        return await self.execute(prompt)