from agents.base_agent import BaseAgent
import logging

logger = logging.getLogger("doutor.senior_dev_ops")

class SeniorDevOpsAgent(BaseAgent):
    def __init__(self, config, router):
        super().__init__("the_senior_dev_ops", config, router)

    async def generate_code(self, plan: dict, context: dict) -> dict:
        prompt = (
            f"Gere código Ops (infra/deploy) para o plano: {plan}. "
            f"Contexto adicional: {context}. "
            "Retorne JSON com: files (dict path->content), deploy_steps (list). "
            "Infra as code, healthchecks, rollback automático, logs estruturados."
        )
        result = await self.execute(prompt, force_chronic=False)
        content = result.get("response", result)
        if isinstance(content, dict) and "content" in content:
            content = content["content"]
        return self._safe_json_parse(str(content))

    async def finalize_code(self, dev_output: dict, dev_feedback: dict) -> dict:
        prompt = (
            "Consolide o código base do Dev Core com as sugestões de melhoria do Dev UI/UX. "
            "Gere a versão final unificada e otimizada. "
            f"Base: {json.dumps(dev_output, indent=2)[:2000]}. "
            f"Feedback/Sugestoes: {json.dumps(dev_feedback, indent=2)[:2000]}. "
            "Retorne JSON com: files (dict path->content, versao final), "
            "deploy_steps (list), merged_conflicts (list)."
        )
        result = await self.execute(prompt, force_chronic=False)
        content = result.get("response", result)
        if isinstance(content, dict) and "content" in content:
            content = content["content"]
        return self._safe_json_parse(str(content))

import json
