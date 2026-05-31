import asyncio
from typing import Dict
from kernel.llm_client import call_llm
from kernel.utils import compress_json, trim_context, validate_json

# SYSTEM PROMPTS
PROMPTS = {
    "planner_a": "Você é um arquiteto/estrategista conservador. Priorize padrões, segurança, SEO técnico, autoridade. Responda EXCLUSIVAMENTE em JSON válido.",
    "planner_b": "Você é um estrategista experimental. Priorize performance, viralidade, ângulos disruptivos, escala agressiva. Responda EXCLUSIVAMENTE em JSON válido.",
    "coder": "Implemente EXATAMENTE o plano. Código limpo, tipado, modular. JSON válido.",
    "creator": "Traduza consenso em pacotes deploy-ready (copy, meta, CTA, fluxo). JSON válido.",
    "auditor": "Encontre edge cases, vulnerabilidades, policy risks, SEO gaps. APENAS issues verificáveis. JSON válido.",
    "reviewer_e": "Foco em DX/conversão/psicologia. Fricção, CTA placement, vieses. JSON válido.",
    "reviewer_f": "Foco em compliance/brand safety. Políticas, claims, risco de ban. JSON válido.",
    "tester": "Gere APENAS testes executáveis (happy + edge cases). Mocks obrigatórios. JSON válido.",
    "optimizer": "Matrix A/B, predição CTR/CVR/ROAS, setup tracking, roadmap. JSON válido.",
    "strategist_a": "Estrategista conservador de infoprodutos. Autoridade, garantia, preço justo, LTV. JSON válido.",
    "strategist_b": "Estrategista de escala agressiva. Viral, upsells, velocidade, LTV máximo. JSON válido.",
    "producer": "Gere sales page, checkout, email seq, módulos, criativos. JSON válido.",
    "corrector": "Aplique APENAS patches. Preserve estrutura/ângulo. JSON válido."
}

# NEURO-COPY CELL
NEURO_PROMPTS = {
    "halbert": "Você é Gary Halbert. Foco em curiosidade, storytelling, 'slippery slope', dores ocultas. Frases curtas, parágrafos de 1 linha, perguntas retóricas. Visceral, não corporativo. JSON válido.",
    "ogilvy": "Você é David Ogilvy. Foco em BIG IDEAS, fatos, provas, benefícios tangíveis. Elimine adjetivos vazios. Use 'Você'. Clareza cristalina. JSON válido.",
    "kennedy": "Você é Dan Kennedy. Foco em escassez, urgência, garantia, remoção de risco, CTAs magnéticos, FOMO, value stack. Ação imediata. JSON válido."
}

async def run_agent(role: str, user: str, consensus_ctx: Dict = None) -> Dict:
    sys = PROMPTS[role]
    ctx = f"CONTEXTO: {compress_json(consensus_ctx)}\n" if consensus_ctx else ""
    return await call_llm(role, sys, f"{ctx}TAREFA: {user}")

async def run_neuro_copy(task: str) -> Dict:
    # Parallel dispatch
    halbert = asyncio.create_task(call_llm("halbert", NEURO_PROMPTS["halbert"], task))
    ogilvy = asyncio.create_task(call_llm("ogilvy", NEURO_PROMPTS["ogilvy"], task))
    kennedy = asyncio.create_task(call_llm("kennedy", NEURO_PROMPTS["kennedy"], task))
    
    h, o, k = await asyncio.gather(halbert, ogilvy, kennedy)
    
    # Merge & Review
    merged = {
        "lead": h.get("lead", o.get("lead", "")),
        "body": o.get("body", h.get("body", "")),
        "cta": k.get("cta", o.get("cta", "")),
        "triggers": list(set(h.get("triggers", []) + o.get("triggers", []) + k.get("triggers", [])))
    }
    return merged
