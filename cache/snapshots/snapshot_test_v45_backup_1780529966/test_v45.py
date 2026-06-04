import asyncio, sys, os
sys.path.insert(0, '.')
from kernel.orchestrator import AntimatterOrchestrator
from kernel.provider_router import ProviderRouter
from kernel.sandbox import Sandbox
from agents.master_key_agent import MasterKeyAgent
from agents.darwin_agent import DarwinAgent

async def test():
    # 1. Sandbox
    sb = Sandbox(os.getcwd())
    result = sb.validate_and_apply({"test_hello.py": "x = 1"}, "test_v45")
    print(f'Sandbox: {result["status"]}, applied: {result["applied"]}')
    assert result["status"] == "success", f'sandbox failed: {result}'
    assert "test_hello.py" in result["applied"]
    os.remove("test_hello.py")

    # 2. Provider Router select_provider
    r = ProviderRouter()
    p = r.select_provider("simple")
    assert p is not None, "select_provider simple returned None"
    print(f'select_provider(simple): {p[0].name}')
    p2 = r.select_provider("complex")
    assert p2 is not None, "select_provider complex returned None"
    print(f'select_provider(complex): {p2[0].name}')

    # 3. MasterKey full backup/restore
    mk = MasterKeyAgent({"role": "the_master_key"}, r)
    bp = await mk.create_full_backup("test_v45_backup")
    assert os.path.exists(bp), "backup path should exist"
    print(f'Full backup: {bp}')

    # 4. Darwin analyze_and_mutate
    da = DarwinAgent({"role": "the_darwin"}, r)
    analysis = await da.analyze_and_mutate()
    assert "status" in analysis, "darwin analyze_and_mutate missing status"
    print(f'Darwin analysis: status={analysis["status"]}, failures={analysis["total_failures"]}')

    # 5. Orchestrator loads 30+ agents with new methods
    orch = AntimatterOrchestrator({'run_id': 'test_v45', 'type': 'test'})
    orch.initialize()
    assert len(orch.agents) >= 30, f'Expected >=30, got {len(orch.agents)}'

    # 6. SeniorDevUiAgent has review_and_suggest
    ui = orch.agents['the_senior_dev_ui']
    assert hasattr(ui, 'review_and_suggest'), 'review_and_suggest missing on UI agent'

    # 7. SeniorDevOpsAgent has finalize_code
    ops = orch.agents['the_senior_dev_ops']
    assert hasattr(ops, 'finalize_code'), 'finalize_code missing on Ops agent'

    # 8. MasterKeyAgent has full backup methods
    assert hasattr(mk, 'create_full_backup'), 'create_full_backup missing'
    assert hasattr(mk, 'restore_full_backup'), 'restore_full_backup missing'

    print('ALL CHECKS PASSED')
    r.close()

asyncio.run(test())
