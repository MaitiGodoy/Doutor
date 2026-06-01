import json, time, asyncio
from typing import Dict, List, Any
from pathlib import Path

from kernel.lateral_agent import LateralAgent
from kernel.state_store import log_audit


class WorkflowEngine:
    def __init__(self):
        self.lateral = LateralAgent()
        self.audit_log = []

    async def compliance_and_resilience_gate(self, target_path: str, context: Dict = None) -> Dict:
        start = time.time()

        scan = await self.lateral.run_defensive_validation(target_path, "comprehensive")

        blocked = scan.get("recommendation") == "patch_required" or scan.get("recommendation") == "human_review"
        alternatives = []
        if blocked:
            alternatives = await self.lateral.generate_alternatives(
                blocked_phase="compliance_gate",
                error_context={"findings": scan.get("findings", []), "recommendation": scan.get("recommendation")},
                budget_status={"limit": 45000, "used": 0}
            )

            for alt in alternatives.get("alternatives", []):
                alt_compliance = await self.lateral.validate_alternative_compliance(alt)
                alt["compliance_validation"] = alt_compliance

        result = {
            "gate": "compliance_and_resilience",
            "target": target_path,
            "passed": not blocked,
            "scan": scan,
            "alternatives": alternatives if blocked else [],
            "blocked": blocked,
            "execution_time_ms": int((time.time() - start) * 1000),
            "status": "blocked" if blocked else "approved",
        }

        log_audit("workflow_engine", "compliance_and_resilience_gate",
                  target_path, json.dumps({"passed": not blocked, "findings": len(scan.get("findings", []))}), "ok")
        return result
