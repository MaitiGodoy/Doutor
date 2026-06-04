import json, logging
from pathlib import Path
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.darwin")

class DarwinAgent(BaseAgent):
    def __init__(self, config, router):
        super().__init__("the_darwin", config, router)
        self.logs_path = Path("logs/audit.jsonl")

    async def mutate_prompt(self, agent_logs: list) -> dict:
        prompt = f"Analise logs e sugira mutacao de prompt: {agent_logs[-5:] if agent_logs else []}. JSON: {{'new_prompt_section': str, 'estimated_savings_pct': int}}"
        result = await self.execute(prompt, force_chronic=False)
        if isinstance(result, dict):
            return {"new_prompt_section": result.get("new_prompt_section", ""), "estimated_savings_pct": int(result.get("estimated_savings_pct", 0))}
        return {"new_prompt_section": "", "estimated_savings_pct": 0}

    async def analyze_and_mutate(self) -> dict:
        failures = []
        costs = []
        mutations = []

        if self.logs_path.exists():
            with open(self.logs_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("status") != "success":
                            failures.append(entry)
                        costs.append(entry.get("cost", 0))
                    except (json.JSONDecodeError, KeyError):
                        pass

        high_cost_agents = {}
        for entry in failures:
            role = entry.get("role", "unknown")
            high_cost_agents[role] = high_cost_agents.get(role, 0) + 1

        for role, count in high_cost_agents.items():
            if count >= 3:
                mutations.append({
                    "role": role,
                    "suggestion": f"Role {role} falhou {count}x. Recomendar revisao de prompt ou ajuste de temperatura.",
                    "fail_count": count
                })

        return {
            "status": "analyzed",
            "total_failures": len(failures),
            "total_cost": sum(costs),
            "mutations_suggested": mutations,
            "high_risk_agents": list(high_cost_agents.keys())
        }
