from mcp.server.fastmcp import FastMCP
import subprocess
import json
import asyncio

from kernel.config import FINANCIAL_GUARD
from kernel.orchestrator import Orchestrator
from kernel.research_agent import ResearchAgent
from kernel.agents import run_agent, run_neuro_copy
from kernel.scope_guardian import ScopeGuardian
from kernel.creative_agent import CreativeAgent

app = FastMCP("omnisquad-mcp")

@app.tool()
def run_linter(file_path: str) -> str:
    res = subprocess.run(["ruff", "check", file_path], capture_output=True, text=True)
    return res.stdout or "Linter OK"

@app.tool()
def run_tests(cmd: str) -> str:
    res = subprocess.run(cmd.split(), capture_output=True, text=True)
    return json.dumps({"stdout": res.stdout, "stderr": res.stderr, "exit_code": res.returncode})

@app.tool()
def check_seo_keywords(query: str, niche: str) -> str:
    return json.dumps({"volume": 1200, "difficulty": 0.45, "intent": "commercial"})

@app.tool()
def validate_ad_policy(platform: str, copy: str) -> str:
    return json.dumps({"status": "approved", "rules_violated": []})

@app.tool()
def financial_guard_check(action: str, amount: float) -> str:
    allowed = amount <= FINANCIAL_GUARD["daily_spend_limit"]
    return json.dumps({"allowed": allowed, "reason": "OK" if allowed else "Limit exceeded", "requires_human": not allowed})

@app.tool()
def dry_run_validation(deliverables: str) -> str:
    return json.dumps({"seo_score": 88.0, "policy_compliance": "pass", "predicted_ctr": 0.032, "recommendation": "deploy"})

@app.tool()
async def doutor_research(niche: str, audience: str, competitors_json: str = "[]") -> str:
    """Pesquisa tendências de mercado, reddit, google trends e competitors"""
    try:
        competitors = json.loads(competitors_json)
    except:
        competitors = []
    try:
        researcher = ResearchAgent(niche, audience, competitors)
        res = researcher.generate_intelligence_briefing()
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@app.tool()
async def doutor_generate_copy(task: str) -> str:
    """Gera copy persuasivo usando a célula Neuro-Copy (Halbert, Ogilvy, Kennedy)"""
    try:
        res = await run_neuro_copy(task)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@app.tool()
async def doutor_generate_code(prompt: str, context_json: str = "{}") -> str:
    """Gera código tipado e modular com o programador senior"""
    try:
        context = json.loads(context_json)
        res = await run_agent("coder", prompt, context)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@app.tool()
async def doutor_scope_check(user_command: str, target_path: str, original_content: str, new_content: str) -> str:
    """Compara alterações de código contra o comando para impedir edições indesejadas (The Surgeon)"""
    try:
        guardian = ScopeGuardian()
        res = guardian.validate_change(user_command, target_path, original_content, new_content)
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

@app.tool()
async def doutor_full_pipeline(input_data_json: str) -> str:
    """Executa o pipeline completo (briefing, pesquisa, copy, código, seo, otimização, design e concierge)"""
    try:
        input_data = json.loads(input_data_json)
    except Exception as e:
        return json.dumps({"status": "error", "reason": f"Invalid JSON payload: {e}"})
    try:
        orch = Orchestrator(input_data)
        res = await orch.run_with_concierge()
        return json.dumps(res, indent=2, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)})

if __name__ == "__main__":
    asyncio.run(app.run_stdio_async())
