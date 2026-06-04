import os
import json
import time
import asyncio
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from kernel.state_manager import StateManager
from kernel.token_manager import TokenManager
from kernel.provider_router import ProviderRouter
from kernel.config import FINANCIAL_GUARD, PRODUCTION
from kernel.concierge import concierge_explain
from kernel.consensus import ConsensusEngine
from kernel.audit_logger import AuditLogger
from kernel.darwin_loop import start_darwin_background
from kernel.notify import escalate_notification
from kernel.lateral_agent import LateralAgent

from kernel.budget_dashboard import generate_dashboard
from kernel.health import health_status
from agents.scout_agent import ScoutAgent
from agents.dual_output_agent import DualOutputAgent
from agents.governance import ConstitutionAgent
from agents.surgeon_agent import SurgeonAgent
from agents.master_key_agent import MasterKeyAgent
from agents.inner_spark_agent import InnerSparkAgent
from agents.omni_aa_agent import OmniAaAgent
from agents.director_agent import DirectorAgent
from agents.senior_dev_agent import SeniorDevAgent
from agents.minimalist_agent import MinimalistAgent
from agents.darwin_agent import DarwinAgent
from agents.gossip_agent import GossipAgent
from agents.prompt_architect_agent import PromptArchitectAgent
from agents.planner_alpha_agent import PlannerAlphaAgent
from agents.planner_beta_agent import PlannerBetaAgent
from agents.senior_dev_core_agent import SeniorDevCoreAgent
from agents.senior_dev_ui_agent import SeniorDevUiAgent
from agents.senior_dev_ops_agent import SeniorDevOpsAgent
from agents.council_protocol import CouncilProtocol
from kernel.resilience_engine import ResilienceEngine
from departments.seo_engine import SEOEngine
from departments.workflow_engine import WorkflowEngine
from meta.team_forge import TeamForge
from meta.inner_spark import InnerSpark
import kernel.mcp_bridge as mcp_bridge

logger = logging.getLogger("doutor.orchestrator")

AGENT_ROLES_MAP = {
    "the_scout":       {"class": ScoutAgent, "config_key": "briefing"},
    "the_polymath":    {"class": None, "config_key": "intelligence"},
    "the_architect":   {"class": None, "config_key": "strategy"},
    "the_director":    {"class": DirectorAgent, "config_key": "executive"},
    "the_constitution":{"class": ConstitutionAgent, "config_key": "constitution"},
    "the_wordsmiths":  {"class": None, "config_key": "creation"},
    "the_senior_dev":  {"class": SeniorDevAgent, "config_key": "senior_dev"},
    "the_voice":       {"class": None, "config_key": "voice"},
    "the_producer":    {"class": DualOutputAgent, "config_key": "dual_output"},
    "the_surgeon":     {"class": SurgeonAgent, "config_key": "surgeon"},
    "the_inspector":   {"class": None, "config_key": "quality"},
    "the_scaler":      {"class": None, "config_key": "optimization"},
    "the_empath":      {"class": None, "config_key": "design"},
    "the_ranker":      {"class": None, "config_key": "seo"},
    "the_lateral":     {"class": LateralAgent, "config_key": "lateral"},
    "the_concierge":   {"class": None, "config_key": "interface"},
    "the_master_key":  {"class": MasterKeyAgent, "config_key": "master_key"},
    "the_zoiao":       {"class": None, "config_key": "zoiao"},
    "the_omni_aa":     {"class": OmniAaAgent, "config_key": "omni_aa"},
    "the_minimalist":  {"class": MinimalistAgent, "config_key": "minimalist"},
    "the_darwin":      {"class": DarwinAgent, "config_key": "darwin"},
    "the_gossip":      {"class": GossipAgent, "config_key": "gossip"},
    "the_chronic":     {"class": None, "config_key": "chronic"},
    "the_inner_spark":      {"class": InnerSparkAgent, "config_key": "inner_spark"},
    "the_prompt_architect": {"class": PromptArchitectAgent, "config_key": "prompt_architect"},
    "the_planner_alpha":    {"class": PlannerAlphaAgent, "config_key": "planner_alpha"},
    "the_planner_beta":     {"class": PlannerBetaAgent, "config_key": "planner_beta"},
    "the_senior_dev_core":  {"class": SeniorDevCoreAgent, "config_key": "senior_dev_core"},
    "the_senior_dev_ui":    {"class": SeniorDevUiAgent, "config_key": "senior_dev_ui"},
    "the_senior_dev_ops":   {"class": SeniorDevOpsAgent, "config_key": "senior_dev_ops"},
}


class AntimatterOrchestrator:
    def __init__(self, input_data: Dict):
        self.input = input_data
        self.run_id = input_data.get("run_id", f"run_{int(time.time())}")
        self.module = self.detect_module()
        self.artifacts: Dict = {}
        self.started_at = time.time()
        self.agents: Dict = {}
        self.master_key: Optional[MasterKeyAgent] = None
        self.lateral_agent = LateralAgent()
        self.seo_engine = SEOEngine()
        self.state_mgr = StateManager()
        self.token_mgr = TokenManager()
        self.provider_router = ProviderRouter()
        self.workflow_engine = WorkflowEngine()
        self.team_forge = TeamForge()
        self.inner_spark = InnerSpark()
        self.root_path = str(Path(__file__).parent.parent)

    def initialize(self):
        roles_dir = Path("agents/roles")
        if roles_dir.exists():
            for role_file in roles_dir.glob("*.json"):
                try:
                    with open(role_file, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    role_name = config.get("role", role_file.stem)
                    agent_info = AGENT_ROLES_MAP.get(role_name, {"class": None, "config_key": role_file.stem})
                    agent_cls = agent_info["class"]
                    if agent_cls:
                        instance = agent_cls(config, self.provider_router)
                        self.agents[role_name] = instance
                    else:
                        from agents.base_agent import BaseAgent
                        instance = BaseAgent(role_name, config, self.provider_router)
                        self.agents[role_name] = instance
                except Exception as e:
                    logger.warning(f"Failed to load agent role {role_file.name}: {e}")

        if "the_master_key" in self.agents:
            self.master_key = self.agents["the_master_key"]
        elif not self.master_key:
            from agents.master_key_agent import MasterKeyAgent
            mk_config = {"role": "the_master_key", "trust_level": "full", "auto_approve_all": True,
                         "silent_execution": True, "snapshot_dir": "cache/snapshots",
                         "blacklisted_commands": ["rm -rf /", ":(){:|:&};:", "mkfs", "dd if=/dev/zero"],
                         "log_path": "logs/master_key_decisions.jsonl", "enable_snapshot": True}
            self.master_key = MasterKeyAgent(mk_config, self.provider_router)
            self.agents["the_master_key"] = self.master_key

        os.environ["MCP_AUTO_APPROVE"] = "true"
        os.environ["INTERACTIVE_MODE"] = "false"
        mcp_bridge.master_key_instance = self.master_key

        self.agents["the_lateral"] = self.lateral_agent
        self.agents["the_ranker"] = self.seo_engine

        self.consensus_engine = ConsensusEngine(self.provider_router)
        self.audit_logger = AuditLogger()

        logger.info(f"Orchestrator initialized with {len(self.agents)} agents")

    def start_background_tasks(self):
        loop = asyncio.get_event_loop()
        loop.create_task(start_darwin_background(self))

    def detect_module(self) -> str:
        txt = json.dumps(self.input).lower()
        if any(k in txt for k in ["code", "func", "api", "debug", "test", "stack", "lint"]):
            return "programming"
        if any(k in txt for k in ["seo", "ads", "copy", "post", "funnel", "keywords", "ctr", "roas", "viral"]):
            return "marketing"
        if any(k in txt for k in ["infoproduto", "curso", "checkout", "lms", "lanÃ§amento", "afiliados", "pre-venda"]):
            return "infoproduct"
        return "multi"

    async def execute(self, input_data: Dict = None) -> Dict:
        start = time.time()
        run_id = self.run_id
        self.current_run_id = run_id
        data = input_data or self.input

        try:
            # 1. SNAPSHOT DE SEGURANCA (OBRIGATORIO)
            logger.info(f"[Orchestrator] {run_id} iniciado. Criando snapshot de seguranca...")
            snapshot_path = await self.agents["the_master_key"].create_full_backup(run_id)

            # 2. BRIEFING + PROMPT ARCHITECT
            raw_briefing = data.get("user_input", "")
            architect = self.agents.get("the_prompt_architect")
            if not architect:
                optimized = {"optimized_context": data, "constraints": []}
            else:
                optimized = await architect.optimize_context(raw_briefing)
                if isinstance(optimized, dict) and optimized.get("status") == "error":
                    optimized = {"optimized_context": data, "constraints": [], "note": "llm_fallback"}

            # 3. CONSELHO OBRIGATORIO (GATE 0)
            logger.info("[Orchestrator] Convocando Conselho para validacao do plano...")
            council = CouncilProtocol(self.agents)
            council_result = await council.convene({"briefing": optimized}, "planning")

            if council_result["status"] == "vetoed":
                logger.warning(f"[Orchestrator] Conselho vetou o plano: {council_result['reason']}")
                return {
                    "status": "blocked",
                    "reason": "council_veto",
                    "details": council_result,
                    "run_id": run_id
                }

            # 4. PLANNERS (Alpha + Beta em paralelo)
            plan_a, plan_b = await asyncio.gather(
                self.agents["the_planner_alpha"].generate_plan(optimized),
                self.agents["the_planner_beta"].generate_plan(optimized),
                return_exceptions=True
            )

            if isinstance(plan_a, Exception) or isinstance(plan_b, Exception):
                raise RuntimeError(f"Falha na geracao de planos: A={'ok' if not isinstance(plan_a, Exception) else plan_a}, B={'ok' if not isinstance(plan_b, Exception) else plan_b}")

            selected_plan = plan_b if (isinstance(plan_b, dict) and plan_b.get("risk_level") == "low") else plan_a

            # 5. DEVS EM CONSENSO (Sequencial, nao paralelo)
            logger.info("[Orchestrator] Dev 1 (Core) gerando base...")
            dev1_output = await self.agents["the_senior_dev_core"].generate_code(selected_plan, optimized)

            logger.info("[Orchestrator] Dev 2 (UI) revisando e sugerindo...")
            dev2_feedback = await self.agents["the_senior_dev_ui"].review_and_suggest(dev1_output.get("files", {}))

            logger.info("[Orchestrator] Dev 3 (Ops) consolidando versao final...")
            final_output = await self.agents["the_senior_dev_ops"].finalize_code(dev1_output, dev2_feedback)

            # 6. SANDBOX VALIDATION (OBRIGATORIO E BLOQUEANTE)
            logger.info("[Orchestrator] Validando no Sandbox...")
            from kernel.sandbox import Sandbox
            sandbox = Sandbox(self.root_path)
            validation_result = sandbox.validate_and_apply(final_output.get("files", {}), run_id)

            if validation_result["status"] == "rejected":
                logger.error(f"[Orchestrator] Sandbox rejeitou codigo: {validation_result['errors']}")
                await self.agents["the_master_key"].restore_full_backup(snapshot_path)
                return {
                    "status": "blocked",
                    "reason": "sandbox_rejection",
                    "errors": validation_result["errors"],
                    "run_id": run_id
                }

            # 7. GATES 3 & 4 (Lateral + Inspector + Constitution)
            lateral_check = await self.lateral_agent.run_defensive_validation(self.root_path, "comprehensive")
            if lateral_check.get("critical"):
                await self.agents["the_master_key"].restore_full_backup(snapshot_path)
                return {"status": "blocked", "reason": "security_veto", "details": lateral_check}

            # 8. EVAL HARNESS (METRICA DE QUALIDADE)
            from kernel.eval_harness import EvalHarness
            eval_harness = EvalHarness()
            quality = eval_harness.validate_output(final_output, "code")

            if quality["score"] < 0.8:
                logger.warning(f"[Orchestrator] Qualidade baixa: {quality['score']}. Pausando para revisao humana.")
                self.state_mgr.save_run(run_id, {"status": "awaiting_human", "quality": quality})
                return {"status": "paused", "reason": "low_quality", "quality": quality, "run_id": run_id}

            # 9. PERSISTENCIA & OBSERVABILIDADE
            from kernel.observability import ObservabilityDB
            obs = ObservabilityDB()
            obs.ingest_jsonl()

            from kernel.semantic_memory import SemanticMemory
            memory = SemanticMemory()
            memory.store(run_id, f"Run {run_id} completed. Quality: {quality['score']}", ["success", "code"])

            # 10. DARWIN (BACKGROUND, NAO BLOQUEANTE)
            asyncio.create_task(self.agents["the_darwin"].analyze_and_mutate())

            return {
                "status": "success",
                "run_id": run_id,
                "quality_score": quality["score"],
                "artifacts": validation_result["applied"],
                "execution_time_ms": int((time.time() - start) * 1000),
                "council_approved": True,
                "sandbox_validated": True
            }

        except Exception as e:
            logger.error(f"[Orchestrator] Falha critica: {e}", exc_info=True)
            try:
                if snapshot_path:
                    await self.agents["the_master_key"].restore_full_backup(snapshot_path)
            except:
                pass
            return {"status": "critical_fail", "error": str(e), "run_id": run_id}
        executed_phases.append({"name": "gate3_quality", "status": "approved" if quality_vote.accepted else "blocked", "conflicts": quality_vote.conflicts})

        # 13. Gate 4: Final consensus (Constitution + Surgeon + Inspector)
        final_vote = await self.consensus_engine.decide(
            question="Should this project be finalized and deployed?",
            context={"artifacts": self.artifacts, "phases": executed_phases},
            agent_roles=["the_constitution", "the_surgeon", "the_inspector"],
            min_votes=3,
        )
        self.artifacts["governance_4"] = {
            "approved": final_vote.accepted,
            "recommendation": final_vote.final_recommendation,
            "conflicts": final_vote.conflicts,
            "escalated": final_vote.escalated,
        }
        executed_phases.append({"name": "gate4_final", "status": "approved" if final_vote.accepted else "blocked", "conflicts": final_vote.conflicts})
        if not final_vote.accepted:
            return await self._abort("gate4_blocked", {"consensus": final_vote.final_recommendation, "conflicts": final_vote.conflicts})

        # 14. Concierge
        try:
            explanation = await concierge_explain(self.artifacts)
            self.artifacts["concierge"] = explanation
            executed_phases.append({"name": "concierge", "status": "success"})
        except Exception:
            executed_phases.append({"name": "concierge", "status": "partial"})

        # 15. Inner Spark aprende com a execução
        inner_spark = self.agents.get("the_inner_spark")
        if inner_spark and hasattr(inner_spark, "analyze_execution"):
            try:
                spark_log = {"run_id": run_id, "phases": executed_phases, "total_tokens": self.token_mgr.get_total_used(), "duration_ms": int((time.time() - start_time) * 1000)}
                spark_result = await inner_spark.analyze_execution(spark_log)
                self.artifacts["inner_spark"] = spark_result
                executed_phases.append({"name": "inner_spark", "status": "analyzed"})
            except Exception:
                executed_phases.append({"name": "inner_spark", "status": "fail"})

        # 16. Eval Harness
        from kernel.eval_harness import EvalHarness
        eval_harness = EvalHarness()
        run_evals = [
            eval_harness.validate_output(optimized, "briefing"),
            eval_harness.validate_output(final_output, "code"),
            eval_harness.validate_output(selected_plan, "plan")
        ]
        quality = eval_harness.aggregate_metrics(run_evals)
        self.artifacts["quality_metrics"] = quality

        # 17. Human-in-the-Loop (pausa se qualidade baixa ou gate crítico)
        if quality["overall_status"] == "review_needed":
            logger.warning("[Orchestrator] Qualidade abaixo do threshold. Aguardando aprovacao humana...")
            self.state_mgr.save_run(run_id, {"status": "awaiting_human", "quality": quality, "paused_at": time.time()})
            return {"status": "paused", "reason": "human_review_required", "quality": quality}

        # 18. Persistencia & Observabilidade
        from kernel.observability import ObservabilityDB
        obs = ObservabilityDB()
        obs.ingest_jsonl()

        from kernel.semantic_memory import SemanticMemory
        memory = SemanticMemory()
        memory.store(run_id, f"Run {run_id} completed. Quality: {quality['avg_quality_score']}", ["auto", "code", "plan"])

        # 19. Darwin (background, nao bloqueante)
        asyncio.create_task(self.agents["the_darwin"].analyze_and_mutate())

        ended_at = time.time()
        status = "completed" if not any(p.get("status") in ("blocked", "fail") for p in executed_phases) else "partial"

        self.state_mgr.save_run(run_id, {"status": status, "module": self.module, "started_at": start_time, "ended_at": ended_at, "tokens_used": self.token_mgr.get_total_used(), "cost_estimate": 0.0, "metadata": {"artifact_count": len(self.artifacts), "phase_count": len(executed_phases)}})
        self.state_mgr.log_audit("orchestrator", "execute_complete", run_id, status)

        return {
            "status": status,
            "run_id": run_id,
            "quality_score": quality["avg_quality_score"],
            "artifacts": self.artifacts,
            "phases": executed_phases,
            "execution_time_ms": int((time.time() - start_time) * 1000)
        }

    async def _abort(self, reason: str, detail: Dict) -> Dict:
        self.state_mgr.save_run(self.run_id, {"status": "blocked", "module": self.module, "started_at": self.started_at, "ended_at": time.time()})
        self.state_mgr.log_audit("orchestrator", reason, self.run_id, json.dumps(detail))
        return {"metadata": {"run_id": self.run_id}, "deliverables": self.artifacts, "status": "blocked", "reason": reason, "detail": detail}

    async def safe_execute_tool(self, tool_name: str, payload: Dict) -> Dict:
        if self.master_key:
            return await self.master_key.bypass_confirmation_loop(tool_name, payload)
        return {"status": "fallback", "message": "Master Key nÃ£o inicializada", "tool": tool_name}

    async def run_with_concierge(self) -> Dict:
        if not self.agents:
            self.initialize()
        result = await self.execute()

        try:
            output_dir = self.input.get("output_dir", ".")
            gate_result = await self.workflow_engine.compliance_and_resilience_gate(output_dir, result)
            result.setdefault("deliverables", {})["compliance_gate"] = gate_result
        except Exception as e:
            result.setdefault("deliverables", {})["compliance_gate"] = {"status": "error", "error": str(e)}

        try:
            explanation = await concierge_explain(result)
        except Exception:
            explanation = {"summary": "Pipeline executado", "status": result.get("status")}

        if PRODUCTION.get("daily_backup_enabled"):
            try:
                self.state_mgr.daily_backup()
            except Exception:
                pass

        if PRODUCTION.get("generate_dashboard"):
            try:
                generate_dashboard()
            except Exception:
                pass

        health = health_status()
        return {
            "system_output": result,
            "human_explanation": explanation,
            "health": health,
            "run_id": self.run_id,
        }

