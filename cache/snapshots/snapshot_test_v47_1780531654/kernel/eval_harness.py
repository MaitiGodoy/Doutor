import json, logging
from typing import Dict, List

logger = logging.getLogger("doutor.eval_harness")

class EvalHarness:
    def __init__(self):
        self.schemas = {
            "code": ["files", "tests"],
            "plan": ["steps", "dependencies", "risk_level"],
            "briefing": ["niche", "audience", "objective", "tone"]
        }

    def validate_output(self, output: dict, category: str) -> dict:
        required = self.schemas.get(category, [])
        missing = [k for k in required if k not in output]
        score = 1.0 - (len(missing) / len(required)) if required else 0.0
        result = {
            "category": category,
            "score": round(score, 2),
            "missing_fields": missing,
            "status": "pass" if score >= 0.8 else "fail"
        }
        logger.info(f"[Eval] {category}: score={result['score']}, status={result['status']}")
        return result

    def aggregate_metrics(self, run_evals: List[dict]) -> dict:
        total_score = sum(e["score"] for e in run_evals) / len(run_evals) if run_evals else 0
        return {
            "avg_quality_score": round(total_score, 2),
            "phases_evaluated": len(run_evals),
            "overall_status": "pass" if total_score >= 0.8 else "review_needed"
        }
