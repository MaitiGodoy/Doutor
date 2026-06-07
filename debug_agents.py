#!/usr/bin/env python3
"""Diagnose agent loading issues"""
import sys, json
sys.path.insert(0, 'C:/Users/User/.gemini/antigravity-ide/scratch/doutor')

# Test loading each agent individually
from kernel.provider_router import ProviderRouter
pr = ProviderRouter()

import_paths = [
    ("the_scout", "agents.scout_agent", "ScoutAgent"),
    ("the_polymath", "agents.polymath_agent", "PolymathAgent"),
    ("the_planner_alpha", "agents.planner_alpha_agent", "PlannerAlphaAgent"),
    ("the_master_key", "agents.master_key_agent", "MasterKeyAgent"),
]

for name, module_path, class_name in import_paths:
    try:
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        config = {"role": name, "max_retries": 0, "timeout": 30}
        instance = cls(config, pr)
        print(f"  OK: {name} ({class_name})")
    except Exception as e:
        print(f"  FAIL: {name}: {e}")
