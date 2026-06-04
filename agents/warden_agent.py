import json, logging, asyncio
from pathlib import Path
from agents.base_agent import BaseAgent
from kernel.anti_entropy import AntiEntropy

logger = logging.getLogger("doutor.warden_agent")

class WardenAgent(BaseAgent):
    def __init__(self, config, router):
        super().__init__("the_warden", config, router)
        self.guard = AntiEntropy(
            str(Path(__file__).parent.parent),
            str(Path(__file__).parent.parent / "baseline" / "spec_v4.7.json")
        )

    async def pre_execution_check(self) -> dict:
        result = self.guard.enforce()
        if result["status"] == "blocked":
            logger.critical(
                f"[Warden] BLOQUEIO ATIVADO: {len(result['violations'])} violacoes "
                f"criticas detectadas."
            )
            return {
                "status": "blocked",
                "message": (
                    "Doutor degradado. Restaure baseline ou corrija violacoes "
                    "antes de prosseguir."
                ),
                "violations": result["violations"]
            }
        return {"status": "approved", "violations": result["violations"]}

    async def post_commit_audit(self):
        result = self.guard.enforce()
        if result["status"] == "blocked":
            logger.error(
                "[Warden] Commit rejeitado: degradacao detectada. "
                "Reverta ou corrija."
            )
            return False
        return True
