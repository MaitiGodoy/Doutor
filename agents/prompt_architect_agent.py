from agents.base_agent import BaseAgent
import logging

logger = logging.getLogger("doutor.prompt_architect")

class PromptArchitectAgent(BaseAgent):
    def __init__(self, config, router):
        super().__init__("the_prompt_architect", config, router)

    async def optimize_context(self, raw_briefing: str) -> dict:
        prompt = (
            f"Otimize este briefing para LLM: {raw_briefing}. "
            "Retorne JSON com: optimized_context (str), constraints (list), few_shot (list), validation_rules (list). "
            "Zero ambiguidade."
        )
        result = await self.execute(prompt, force_chronic=False)
        content = result.get("response", result)
        if isinstance(content, dict) and "content" in content:
            content = content["content"]
        return self._safe_json_parse(str(content))

# log marker - no emoji
