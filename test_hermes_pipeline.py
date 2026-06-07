#!/usr/bin/env python3
"""Test Hermes integration in Doutor pipeline"""
import asyncio
import sys
sys.path.insert(0, 'C:/Users/User/.gemini/antigravity-ide/scratch/doutor')

async def test():
    # Teste 1: Hermes bridge direct call via _ask_ollama
    print("=== Teste 1: Hermes direct Ollama call ===")
    from kernel.hermes_bridge import HermesBridge
    hb = HermesBridge()
    result = await hb._ask_ollama(
        system="You are a test assistant.",
        prompt="Say only the word: TESTE_OK"
    )
    resp = str(result.get("response", ""))[:80]
    print(f"  Hermes response: {resp}")
    print(f"  Status: {result.get('status')}")
    print(f"  Via: {result.get('via')}")

    # Teste 1b: participate_council
    print("  (testando participate_council...)")
    result2 = await hb.participate_council(
        {"action": "test", "task": "Council test"},
        {"plan": "test", "rationale": "testing"}
    )
    resp2 = str(result2.get("response", ""))[:80]
    print(f"  Council response: {resp2}")

    # Teste 2: Pipeline completo com Hermes
    print()
    print("=== Teste 2: Pipeline completo com Hermes ===")
    task_input = {"task": "Gere uma meta description SEO de 160 caracteres para um site de receitas veganas"}
    from kernel.orchestrator import AntimatterOrchestrator
    orch = AntimatterOrchestrator(input_data=task_input)
    orch.initialize()  # Carrega todos os agentes
    print(f"  Agents loaded: {len(orch.agents)}")
    result = await orch.execute(task_input)
    print(f"  Pipeline status: {result.get('status', '?')}")
    final = result.get("final_output", "")
    print(f"  Final output: {str(final)[:200]}...")
    print(f"  Hermes stages: {len(result.get('hermes_participation', []))}")

    # Teste 3: Hermes health
    print()
    print("=== Teste 3: Hermes bridge insights ===")
    status = await hb.get_status()
    print(f"  Model: {status.get('model')}")
    print(f"  Call count: {hb.call_count}")

    # Teste 4: SEO com Hermes
    print()
    print("=== Teste 4: SEO Orchestrator com Hermes ===")
    from kernel.seo_orchestrator import SEOOrchestrator
    seo = SEOOrchestrator()
    blog = await seo.generate_blog(
        topic="Vegan protein sources",
        audience="Brazilian vegans",
        keywords="proteina vegana, fontes de proteina vegetal"
    )
    print(f"  Blog status: {blog.get('status')}")
    print(f"  Hermes suggestions: {bool(blog.get('data', {}).get('hermes_suggestions'))}")

    print()
    print("Todos os testes concluidos com sucesso!")

asyncio.run(test())
