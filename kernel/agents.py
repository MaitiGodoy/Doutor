import asyncio
from typing import Dict, Optional
from kernel.llm_client import call_llm
from kernel.provider_router import ProviderRouter, AGENT_MODEL_MAP
from kernel.utils import compress_json

_ROUTER: Optional[ProviderRouter] = None

def _get_router() -> ProviderRouter:
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = ProviderRouter()
    return _ROUTER

# Legacy role → new agent role mapping
ROLE_ALIASES = {
    "planner_a": "the_architect",
    "planner_b": "the_polymath",
    "coder": "the_senior_dev",
    "creator": "the_wordsmiths",
    "auditor": "the_inspector",
    "reviewer_e": "the_constitution",      # Doutor 5.0: Hermes-backed reviewer
    "reviewer_f": "the_ranker",
    "tester": "the_surgeon",
    "optimizer": "the_scaler",
    "strategist_a": "the_architect",
    "strategist_b": "the_polymath",
    "producer": "the_producer",
}

async def run_agent(role: str, user: str, consensus_ctx: Dict = None) -> Dict:
    agent_role = ROLE_ALIASES.get(role, role)
    ctx = f"CONTEXTO: {compress_json(consensus_ctx)}\n" if consensus_ctx else ""
    return await call_llm(agent_role, f"You are {agent_role}. Respond in valid JSON.", f"{ctx}TASK: {user}")

async def run_neuro_copy(task: str) -> Dict:
    halbert = asyncio.create_task(call_llm("halbert", "You are Gary Halbert. Persuasive copy.", task))
    ogilvy = asyncio.create_task(call_llm("ogilvy", "You are David Ogilvy. Big ideas, facts, proofs.", task))
    kennedy = asyncio.create_task(call_llm("kennedy", "You are Dan Kennedy. Urgency, scarcity, CTA.", task))

    h, o, k = await asyncio.gather(halbert, ogilvy, kennedy)

    merged = {
        "lead": h.get("lead", o.get("lead", "")),
        "body": o.get("body", h.get("body", "")),
        "cta": k.get("cta", o.get("cta", "")),
        "triggers": list(set(h.get("triggers", []) + o.get("triggers", []) + k.get("triggers", [])))
    }
    return merged
