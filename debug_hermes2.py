#!/usr/bin/env python3
"""Debug Hermes SSH command"""
import asyncio, sys, json
sys.path.insert(0, 'C:/Users/User/.gemini/antigravity-ide/scratch/doutor')

async def test():
    from kernel.hermes_bridge import HermesBridge
    hb = HermesBridge()
    r = await hb._ask_ollama('test', 'Say TESTE_OK')
    print(json.dumps(r, indent=2, default=str))

asyncio.run(test())
