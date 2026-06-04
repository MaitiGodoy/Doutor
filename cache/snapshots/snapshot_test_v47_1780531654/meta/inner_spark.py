import os
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class InnerSpark:
    def __init__(self):
        self.log_path = Path("logs/spark_observations.jsonl")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    async def observe_and_learn(self, pipeline_result: Dict) -> Dict:
        start = time.time()
        observations = []

        gate_results = pipeline_result.get("compliance_gate", {})
        if gate_results.get("blocked"):
            observations.append({
                "type": "compliance_block",
                "detail": "Pipeline bloqueado no compliance gate",
                "suggestion": "Revisar configurações de compliance ou ajustar escopo",
            })

        artifacts = pipeline_result.get("deliverables", {})
        for key, val in artifacts.items():
            if isinstance(val, dict):
                status = val.get("status", val.get("recommendation", "unknown"))
                if status in ("error", "blocked", "patch_required"):
                    observations.append({
                        "type": f"phase_{key}_failure",
                        "detail": f"Fase {key} retornou {status}",
                        "suggestion": f"Revisar inputs da fase {key} ou aumentar budget",
                    })

        meta = pipeline_result.get("metadata", {})
        tokens = meta.get("tokens_used", 0)
        if tokens > 30000:
            observations.append({
                "type": "high_token_consumption",
                "detail": f"Pipeline consumiu {tokens} tokens",
                "suggestion": "Ativar modo diff-only ou reduzir max_tokens por fase",
            })

        entry = {
            "timestamp": time.time(),
            "run_id": pipeline_result.get("run_id", pipeline_result.get("metadata", {}).get("run_id", "unknown")),
            "observations": observations,
            "observation_count": len(observations),
            "insights": self._generate_insights(observations),
            "elapsed_ms": int((time.time() - start) * 1000),
        }

        self._log(entry)
        return entry

    def _generate_insights(self, observations: List[Dict]) -> List[str]:
        insights = []
        obs_types = [o["type"] for o in observations]

        if "compliance_block" in obs_types:
            insights.append("Governança está bloqueando execuções — revisar regras do Constitution/Surgeon")
        if "high_token_consumption" in obs_types:
            insights.append("Consumo de tokens alto — considerar compressão de contexto")
        failure_count = sum(1 for t in obs_types if t.endswith("_failure"))
        if failure_count >= 3:
            insights.append("Múltiplas fases falhando — possível problema estrutural no pipeline")
        if not insights:
            insights.append("Nenhum padrão negativo detectado — pipeline saudável")

        return insights

    def _log(self, entry: Dict):
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass
