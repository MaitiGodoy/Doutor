#!/usr/bin/env python3
"""Verifica todos os 30+ agentes do Doutor"""
import sys, importlib, traceback
sys.path.insert(0, 'C:/Users/User/.gemini/antigravity-ide/scratch/doutor')

AGENTS = {
    "the_scout": ("agents.scout_agent", "ScoutAgent"),
    "the_polymath": ("agents.polymath_agent", "PolymathAgent"),
    "the_architect": ("agents.strategy_agent", "StrategyAgent"),
    "the_director": ("agents.director_agent", "DirectorAgent"),
    "the_constitution": ("agents.governance", "ConstitutionAgent"),
    "the_wordsmiths": ("agents.wordsmiths_agent", "WordsmithsAgent"),
    "the_senior_dev": ("agents.senior_dev_agent", "SeniorDevAgent"),
    "the_voice": ("agents.voice_agent", "VoiceAgent"),
    "the_producer": ("agents.dual_output_agent", "DualOutputAgent"),
    "the_surgeon": ("agents.surgeon_agent", "SurgeonAgent"),
    "the_inspector": ("agents.quality_agent", "QualityAgent"),
    "the_scaler": ("agents.optimizer_agent", "OptimizerAgent"),
    "the_empath": ("agents.design_agent", "DesignAgent"),
    "the_ranker": ("agents.ranker_agent", "RankerAgent"),
    "the_lateral": ("kernel.lateral_agent", "LateralAgent"),
    "the_concierge": ("agents.concierge_agent", "ConciergeAgent"),
    "the_master_key": ("agents.master_key_agent", "MasterKeyAgent"),
    "the_zoiao": ("agents.zoiao_agent", "ZoiaoAgent"),
    "the_inner_spark": ("agents.inner_spark_agent", "InnerSparkAgent"),
    "the_omni_aa": ("agents.omni_aa_agent", "OmniAaAgent"),
    "the_minimalist": ("agents.minimalist_agent", "MinimalistAgent"),
    "the_darwin": ("agents.darwin_agent", "DarwinAgent"),
    "the_gossip": ("agents.gossip_agent", "GossipAgent"),
    "the_chronic": ("agents.chronic_agent", "ChronicAgent"),
    "the_prompt_architect": ("agents.prompt_architect_agent", "PromptArchitectAgent"),
    "the_planner_alpha": ("agents.planner_alpha_agent", "PlannerAlphaAgent"),
    "the_planner_beta": ("agents.planner_beta_agent", "PlannerBetaAgent"),
    "the_senior_dev_core": ("agents.senior_dev_core_agent", "SeniorDevCoreAgent"),
    "the_senior_dev_ui": ("agents.senior_dev_ui_agent", "SeniorDevUiAgent"),
    "the_senior_dev_ops": ("agents.senior_dev_ops_agent", "SeniorDevOpsAgent"),
    "the_warden": ("agents.warden_agent", "WardenAgent"),
    "CouncilProtocol": ("agents.council_protocol", "CouncilProtocol"),
    "ResilienceEngine": ("kernel.resilience_engine", "ResilienceEngine"),
    "WorkflowEngine": ("departments.workflow_engine", "WorkflowEngine"),
    "TeamForge": ("meta.team_forge", "TeamForge"),
    "InnerSpark": ("meta.inner_spark", "InnerSpark"),
    "HermesBridge": ("kernel.hermes_bridge", "HermesBridge"),
    "SEOOrchestrator": ("kernel.seo_orchestrator", "SEOOrchestrator"),
    "GrowthAgent": ("kernel.growth_agent", "GrowthAgent"),
    "CouncilAgent": ("kernel.council_agent", "CouncilAgent"),
}

print(f"=== Verificando {len(AGENTS)} modulos/agentes do Doutor ===\n")

ok = 0
fail = 0
for name, (module_path, class_name) in sorted(AGENTS.items()):
    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        print(f"  [OK] {name:25s} -> {module_path}.{class_name}")
        ok += 1
    except Exception as e:
        print(f"  [FAIL] {name:25s} -> {module_path}.{class_name}")
        print(f"         Erro: {e}")
        traceback.print_exc(limit=1, file=sys.stdout)
        fail += 1

print(f"\n=== Total: {ok} OK, {fail} FAIL ===")
sys.exit(0 if fail == 0 else 1)
