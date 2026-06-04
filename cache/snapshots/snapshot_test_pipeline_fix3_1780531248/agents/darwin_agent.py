import os, json, time, hashlib
from pathlib import Path
from agents.base_agent import BaseAgent

class DarwinAgent(BaseAgent):
    def __init__(self, config, router):
        super().__init__("the_darwin", config, router)
        self.logs_dir = Path("logs")
        self.quarantine_dir = Path("cache/quarantine_prompts")
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.promotion_threshold = 0.7
        self.min_runs = 3

    async def mutate_prompt(self, agent_logs: list) -> dict:
        prompt = f"Analise logs e sugira mutacao de prompt: {agent_logs[-5:] if agent_logs else []}. JSON: {{'new_prompt_section': str, 'estimated_savings_pct': int}}"
        result = await self.execute(prompt, force_chronic=False)
        if isinstance(result, dict):
            return {"new_prompt_section": result.get("new_prompt_section", ""), "estimated_savings_pct": int(result.get("estimated_savings_pct", 0))}
        return {"new_prompt_section": "", "estimated_savings_pct": 0}

    async def analyze_and_mutate(self) -> dict:
        log_files = list(self.logs_dir.glob("*_audit.jsonl"))
        if not log_files:
            return {"status": "skip", "reason": "no_logs"}

        agent_metrics = {}
        for lf in log_files:
            with open(lf, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        role = entry.get("role", "unknown")
                        if role not in agent_metrics:
                            agent_metrics[role] = {"runs": 0, "fails": 0, "total_tokens": 0, "cost": 0.0}
                        agent_metrics[role]["runs"] += 1
                        if entry.get("status") != "success":
                            agent_metrics[role]["fails"] += 1
                        agent_metrics[role]["total_tokens"] += entry.get("tokens", 0)
                        agent_metrics[role]["cost"] += entry.get("cost", 0.0)
                    except:
                        continue

        mutations = []
        for role, metrics in agent_metrics.items():
            fail_rate = metrics["fails"] / metrics["runs"] if metrics["runs"] > 0 else 0
            avg_cost = metrics["cost"] / metrics["runs"] if metrics["runs"] > 0 else 0

            if fail_rate > 0.3 or avg_cost > 0.05:
                prompt_path = Path(f"prompts/the_{role.replace('the_', '')}.md")
                if prompt_path.exists():
                    current_prompt = prompt_path.read_text(encoding="utf-8")
                    mutation_prompt = f"""
Analise o prompt atual e sugira uma versao otimizada que reduza falhas/custo.
Prompt Atual: {current_prompt[:500]}
Metricas: fails={fail_rate:.2f}, avg_cost={avg_cost:.4f}
Retorne APENAS o novo prompt completo.
"""
                    mutated = await self.execute(mutation_prompt)
                    content = mutated.get("response", {}).get("content", "")
                    if content.strip():
                        mutant_path = self.quarantine_dir / f"{role}_v{int(time.time())}.md"
                        mutant_path.write_text(content, encoding="utf-8")
                        mutations.append({"role": role, "path": str(mutant_path), "metrics": metrics})

        return {"status": "analyzed", "mutations": mutations, "total_analyzed": len(agent_metrics)}

    async def promote_mutation(self, role: str, mutant_path: str) -> dict:
        target = Path(f"prompts/the_{role.replace('the_', '')}.md")
        if target.exists():
            target.write_text(Path(mutant_path).read_text(encoding="utf-8"), encoding="utf-8")
            return {"status": "promoted", "role": role}
        return {"status": "fail", "reason": "target_prompt_missing"}
