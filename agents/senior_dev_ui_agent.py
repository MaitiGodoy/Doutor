from agents.base_agent import BaseAgent
import logging

logger = logging.getLogger("doutor.senior_dev_ui")

class SeniorDevUiAgent(BaseAgent):
    def __init__(self, config, router):
        super().__init__("the_senior_dev_ui", config, router)

    async def generate_code(self, plan: dict, context: dict) -> dict:
        prompt = (
            f"Gere código UI (frontend) para o plano: {plan}. "
            f"Contexto adicional: {context}. "
            "Retorne JSON com: files (dict path->content), lighthouse_score_target (int 95). "
            "Mobile-first, Core Web Vitals, zero layout shift."
        )
        result = await self.execute(prompt, force_chronic=False)
        content = result.get("response", result)
        if isinstance(content, dict) and "content" in content:
            content = content["content"]
        return self._safe_json_parse(str(content))

    async def review_and_suggest(self, core_files: dict) -> dict:
        prompt = (
            "Revise o seguinte código gerado pelo Dev Core e sugira melhorias visuais, funcionais e de UX. "
            f"Código: {json.dumps(core_files, indent=2)[:3000]}. "
            "Retorne JSON com: suggestions (list of dicts com file_path e suggestion), "
            "critical_changes (list), ux_score (int 0-100)."
        )
        result = await self.execute(prompt, force_chronic=False)
        content = result.get("response", result)
        if isinstance(content, dict) and "content" in content:
            content = content["content"]
        return self._safe_json_parse(str(content))

