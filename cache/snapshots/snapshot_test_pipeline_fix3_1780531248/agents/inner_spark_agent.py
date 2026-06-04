import os, json, time, logging
from pathlib import Path
from typing import Dict
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.inner_spark")

class InnerSparkAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_inner_spark", config, router)
        self.memory_path = Path(config.get("log_path", "logs/inner_spark_memory.jsonl"))
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)

    async def analyze_execution(self, run_log: Dict) -> Dict:
        if not run_log or "phases" not in run_log:
            return {"status": "skip", "reason": "no_execution_data"}

        failures = [p for p in run_log["phases"] if p.get("status") == "fail"]
        high_cost = [p for p in run_log["phases"] if p.get("tokens_used", 0) > 3000]
        slow = [p for p in run_log["phases"] if p.get("duration_ms", 0) > 10000]

        insights = []
        if failures:
            insights.append(f"{len(failures)} falhas em: {[f['name'] for f in failures]}")
        if high_cost:
            insights.append(f"Custo alto em: {[h['name'] for h in high_cost]}")
        if slow:
            insights.append(f"Lentidão em: {[s['name'] for s in slow]}")
        if not insights:
            insights.append("Pipeline saudável. Nenhum padrão negativo detectado.")

        pattern = {"run_id": run_log.get("run_id"), "timestamp": time.time(), "insights": insights, "metrics": {"total_tokens": run_log.get("total_tokens"), "duration_ms": run_log.get("duration_ms")}}
        with open(self.memory_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(pattern, default=str) + "\n")

        return {"status": "analyzed", "insights": insights, "patterns_saved": True}

# EOF
