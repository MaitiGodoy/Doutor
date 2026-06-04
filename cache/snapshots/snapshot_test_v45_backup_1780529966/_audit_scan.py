"""Audit: find broken imports, dead code, unconnected modules"""
import sys, os, importlib, ast, json
sys.path.insert(0, '.')

modules = [
    'kernel.config', 'kernel.utils', 'kernel.provider_router',
    'kernel.provider_quotas', 'kernel.state_store', 'kernel.llm_client',
    'kernel.orchestrator', 'kernel.sandbox', 'kernel.scheduler',
    'kernel.health', 'kernel.budget_dashboard', 'kernel.lateral_agent',
    'kernel.concierge', 'kernel.notify', 'kernel.research_agent',
    'kernel.creative_agent', 'kernel.scope_guardian', 'kernel.tokens_policy',
    'kernel.mcp_bridge', 'kernel.agents', 'kernel.agent_bridge',
    'agents.base_agent', 'agents.master_key',
]

issues = []

# 1. Test each import
for m in modules:
    try:
        importlib.import_module(m)
        print(f"  OK: {m}")
    except ImportError as e:
        print(f"  FAIL: {m} -> {e}")
        issues.append({"module": m, "error": str(e)})
    except Exception as e:
        print(f"  ERROR: {m} -> {e}")
        issues.append({"module": m, "error": str(e)})

# 2. Check files that exist but are NOT imported anywhere
print("\n--- Files possibly unused ---")
all_py_files = set()
for root, dirs, files in os.walk('.'):
    if '__pycache__' in root or '.git' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            rel = os.path.join(root, f)[2:].replace('\\', '.').replace('.py', '')
            all_py_files.add(rel)

imported_modules = set(m.split('.')[0] + '.' + m.split('.')[1] if '.' in m else m for m in modules)
# Check which py files are never referenced
for py_mod in sorted(all_py_files):
    # Skip __init__, setup scripts
    if py_mod.startswith('_') or py_mod in ('test_run', 'deserialize_escopo', 'extract_chat', 'find_code_blocks'):
        continue
    mod_path = py_mod.replace('.', '/') + '.py'
    if not os.path.exists(mod_path):
        continue
    # Check if any other file imports it
    found = False
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in root or '.git' in root:
            continue
        for f in files:
            if not f.endswith('.py'):
                continue
            fp = os.path.join(root, f)
            try:
                content = open(fp, encoding='utf-8', errors='ignore').read()
                if f'import {py_mod}' in content or f'from {py_mod}' in content:
                    found = True
                    break
            except:
                pass
        if found:
            break
    if not found:
        print(f"  UNUSED: {py_mod}.py — never imported by any other module")
        issues.append({"type": "unused_file", "file": f"{py_mod}.py"})

# 3. Check config references to non-existent files
print("\n--- Config referencing missing files ---")
config_refs = {
    'kernel.config.PRODUCTION.low_power_fallback_model': 'microsoft/phi-3.5-mini-instruct',
    'kernel.config.PRODUCTION.cron_schedule': '0 8 * * *',
}
# Check lateral.json refs
try:
    with open('agents/roles/lateral.json') as f:
        lat = json.load(f)
    prompt_file = lat.get('system_prompt_file', '')
    log_file = lat.get('log_to', '')
    for ref in [prompt_file, log_file]:
        if not os.path.exists(ref):
            print(f"  MISSING: lateral.json refs '{ref}' — file not found")
            issues.append({"type": "missing_config_ref", "file": ref})
except Exception as e:
    print(f"  ERROR reading lateral.json: {e}")

# Check master_key.json refs
try:
    with open('agents/roles/master_key.json') as f:
        mk = json.load(f)
    for ref_key in ['snapshot_dir', 'log_path']:
        ref = mk.get(ref_key, '')
        dir_path = os.path.dirname(ref) if '.' in ref else ref
        if ref and not os.path.exists(dir_path):
            print(f"  MISSING: master_key.json '{ref_key}': '{ref}' — dir not found")
            issues.append({"type": "missing_config_dir", "key": ref_key, "path": ref})
except Exception as e:
    print(f"  ERROR reading master_key.json: {e}")

# 4. Check .env vs config expectations
print("\n--- Env vars expected but not in .env ---")
from kernel.config import PRODUCTION
expected_env = ['WEBHOOK_SECRET', 'CRON_SCHEDULE', 'MAX_DAILY_RUN_HOURS']
for var in expected_env:
    val = os.getenv(var)
    if not val or val == 'change-me':
        print(f"  MISSING or DEFAULT: {var}={val}")
        issues.append({"type": "missing_env", "var": var, "value": val})

# 5. Check test files exist but have no test runner
print("\n--- Test files without runner ---")
if os.path.exists('tests/test_fuzz.py') and not any('pytest' in open(f, errors='ignore').read() for f in ['main.py', 'mcp_server.py', 'test_run.py'] if os.path.exists(f)):
    print("  ORPHAN: tests/ — exists but no pytest config or runner script")
    issues.append({"type": "orphan_tests", "path": "tests/"})

# Summary
print(f"\n{'='*50}")
if issues:
    print(f"ISSUES FOUND: {len(issues)}")
    for i in issues:
        print(f"  - {json.dumps(i, ensure_ascii=False)}")
else:
    print("NO ISSUES FOUND")
