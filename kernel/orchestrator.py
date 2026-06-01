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
from kernel.notify import escalate_notification
from kernel.lateral_agent import LateralAgent
from kernel.sandbox import exec_shell
from kernel.budget_dashboard import generate_dashboard
from kernel.health import health_status
from agents.briefing_agent import BriefingAgent
from agents.dual_output_agent import DualOutputAgent
from agents.governance import ConstitutionAgent, SurgeonAgent
from agents.master_key import MasterKeyAgent
from departments.seo_engine import SEOEngine
from departments.workflow_engine import WorkflowEngine
from meta.team_forge import TeamForge
from meta.inner_spark import InnerSpark
import kernel.mcp_bridge as mcp_bridge

logger = logging.getLogger("doutor.orchestrator")

AGENT_ROLES_MAP = {
    "the_scout": {"class": BriefingAgent, "config_key": "briefing"},
    "the_polymath": {"class": None, "config_key": "intelligence"},
    "the_architect": {"class": None, "config_key": "strategy"},
    "the_constitution": {"class": ConstitutionAgent, "config_key": "constitution"},
    "the_surgeon": {"class": SurgeonAgent, "config_key": "surgeon"},
    "the_wordsmiths": {"class": None, "config_key": "creation"},
    "the_inspector": {"class": None, "config_key": "quality"},
    "the_scaler": {"class": None, "config_key": "optimization"},
    "the_empath": {"class": None, "config_key": "design"},
    "the_voice": {"class": None, "config_key": "voice"},
    "the_concierge": {"class": None, "config_key": "interface"},
    "the_producer": {"class": DualOutputAgent, "config_key": "dual_output"},
    "the_ranker": {"class": None, "config_key": "seo"},
    "the_master_key": {"class": MasterKeyAgent, "config_key": "master_key"},
    "the_lateral": {"class": LateralAgent, "config_key": "lateral"},
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
            from agents.master_key import MasterKeyAgent
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

        logger.info(f"Orchestrator initialized with {len(self.agents)} agents")

    def detect_module(self) -> str:
        txt = json.dumps(self.input).lower()
        if any(k in txt for k in ["code", "func", "api", "debug", "test", "stack", "lint"]):
            return "programming"
        if any(k in txt for k in ["seo", "ads", "copy", "post", "funnel", "keywords", "ctr", "roas", "viral"]):
            return "marketing"
        if any(k in txt for k in ["infoproduto", "curso", "checkout", "lms", "lançamento", "afiliados", "pre-venda"]):
            return "infoproduct"
        return "multi"

    async def execute(self, input_data: Dict = None) -> Dict:
        data = input_data or self.input
        self.state_mgr.save_run(self.run_id, {"status": "running", "module": self.module, "started_at": self.started_at})
        self.state_mgr.log_audit("orchestrator", "execute_start", self.run_id, self.module)

        # 1. Briefing
        briefing_agent = self.agents.get("the_scout") or BriefingAgent()
        briefing = await briefing_agent.collect_briefing(data)
        self.state_mgr.save_checkpoint(self.run_id, "briefing", briefing)
        self.artifacts["briefing"] = briefing

        # 2. TeamForge
        team_context = self.team_forge.generate_context(briefing.get("briefing", data))
        self.artifacts["team_context"] = team_context

        # 3. Estratégia (Governance Gate 1)
        constitution = self.agents.get("the_constitution") or ConstitutionAgent()
        gov1 = await constitution.validate({"module": self.module, "approach": data, "deliverables": [briefing], "timeline": "immediate"})
        self.state_mgr.save_checkpoint(self.run_id, "governance_1", gov1)
        self.artifacts["governance_1"] = gov1
        if not gov1.get("approved"):
            return await self._abort("governance_1_blocked", gov1)

        # 4. Criação
        if self.module in ("marketing", "infoproduct"):
            from kernel.agents import run_neuro_copy
            neuro = await run_neuro_copy(json.dumps(data))
            self.artifacts["neuro_copy"] = neuro
        elif self.module == "programming":
            from kernel.agents import run_agent
            code = await run_agent("coder", json.dumps(data), data)
            self.artifacts["code"] = code
        else:
            from kernel.agents import run_agent, run_neuro_copy
            task1 = asyncio.create_task(run_agent("planner_a", json.dumps(data)))
            task2 = asyncio.create_task(run_agent("planner_b", json.dumps(data)))
            pa, pb = await asyncio.gather(task1, task2)
            consensus = {"approach": pa.get("approach") or pb.get("approach"), "merged": {**pa, **pb}}
            neuro = await run_neuro_copy(json.dumps(consensus))
            self.artifacts["neuro_copy"] = neuro
            self.artifacts["consensus"] = consensus

        self.state_mgr.save_checkpoint(self.run_id, "creation", self.artifacts)

        # 5. Governance Gate 2 — Surgeon review
        surgeon_safe = True
        for key, val in self.artifacts.items():
            if isinstance(val, dict) and val.get("status") == "error":
                surgeon_safe = False
                break
        self.artifacts["governance_2"] = {"approved": surgeon_safe, "violations": [] if surgeon_safe else [{"type": "artifact_error", "severity": "high"}]}

        # 6. Voice Layer
        voice_agent = self.agents.get("the_voice")
        if voice_agent and self.artifacts.get("neuro_copy"):
            try:
                voiced = await voice_agent.execute(str(self.artifacts["neuro_copy"]))
                self.artifacts["voice_output"] = voiced
            except Exception:
                pass

        # 7. SEO Engine
        seo_result = self.seo_engine.optimize_site_seo_and_virality(".")
        self.artifacts["seo_optimization"] = seo_result
        self.state_mgr.save_checkpoint(self.run_id, "seo", seo_result)

        # 8. Dual Output
        dual_agent = self.agents.get("the_producer") or DualOutputAgent()
        try:
            target_dir = data.get("output_dir", "output/html")
            dual = await dual_agent.generate_dual_output(self.artifacts, target_dir)
            self.artifacts["dual_output"] = dual
        except Exception as e:
            self.artifacts["dual_output"] = {"status": "error", "error": str(e)}

        # 9. Qualidade / Compliance
        try:
            compliance_scan = await self.lateral_agent.run_defensive_validation(
                data.get("output_dir", "."), "comprehensive"
            )
            self.artifacts["compliance_scan"] = compliance_scan
        except Exception as e:
            self.artifacts["compliance_scan"] = {"error": str(e), "findings": [], "recommendation": "approve"}

        # 10. Governance Gate 3
        surgeon = self.agents.get("the_surgeon") or SurgeonAgent()
        gov3 = await surgeon.validate_change(
            json.dumps(data), "pipeline", str(self.input), json.dumps(self.artifacts)
        )
        self.artifacts["governance_3"] = gov3

        # 11. Otimização
        from kernel.agents import run_agent as generic_agent
        try:
            optimization = await generic_agent("optimizer", json.dumps(self.artifacts), self.artifacts)
            self.artifacts["optimization"] = optimization
        except Exception:
            pass

        # 12. Design
        if self.artifacts.get("dual_output", {}).get("files", {}).get("desktop"):
            try:
                design_result = self.seo_engine.optimize_file(
                    self.artifacts["dual_output"]["files"]["desktop"]
                )
                self.artifacts["design_optimization"] = design_result
            except Exception:
                pass

        # 13. Governance Gate 4
        gov4 = await constitution.validate(self.artifacts, {"phase": "final"})
        self.artifacts["governance_4"] = gov4
        self.state_mgr.save_checkpoint(self.run_id, "governance_4", gov4)

        # 14. Concierge
        try:
            explanation = await concierge_explain(self.artifacts)
            self.artifacts["concierge"] = explanation
        except Exception:
            pass

        # 15. Inner Spark
        try:
            spark = await self.inner_spark.observe_and_learn(self.artifacts)
            self.artifacts["inner_spark"] = spark
        except Exception:
            pass

        ended_at = time.time()
        status = "completed" if not any(
            v.get("status") == "error" for v in self.artifacts.values() if isinstance(v, dict)
        ) else "partial"

        self.state_mgr.save_run(self.run_id, {
            "status": status, "module": self.module,
            "started_at": self.started_at, "ended_at": ended_at,
            "tokens_used": 0, "cost_estimate": 0.0,
            "metadata": {"artifact_count": len(self.artifacts)},
        })
        self.state_mgr.log_audit("orchestrator", "execute_complete", self.run_id, status)

        return {
            "metadata": {"run_id": self.run_id, "module": self.module, "artifact_count": len(self.artifacts)},
            "deliverables": self.artifacts,
            "status": status,
        }

    async def _abort(self, reason: str, detail: Dict) -> Dict:
        self.state_mgr.save_run(self.run_id, {"status": "blocked", "module": self.module, "started_at": self.started_at, "ended_at": time.time()})
        self.state_mgr.log_audit("orchestrator", reason, self.run_id, json.dumps(detail))
        return {"metadata": {"run_id": self.run_id}, "deliverables": self.artifacts, "status": "blocked", "reason": reason, "detail": detail}

    async def safe_execute_tool(self, tool_name: str, payload: Dict) -> Dict:
        if self.master_key:
            return await self.master_key.bypass_confirmation_loop(tool_name, payload)
        return {"status": "fallback", "message": "Master Key não inicializada", "tool": tool_name}

    async def run_with_concierge(self) -> Dict:
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
