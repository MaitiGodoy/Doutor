#!/bin/bash
echo "[WARDEN] Executando verificacao anti-degradacao..."
python -c "
import asyncio, sys
sys.path.insert(0, '.')
from agents.warden_agent import WardenAgent
agent = WardenAgent({}, None)
result = asyncio.run(agent.post_commit_audit())
if not result:
    print('\u274c Commit bloqueado pelo Warden. Degradacao detectada.')
    sys.exit(1)
print('\u2705 Warden aprovou commit. Nenhuma degradacao detectada.')
sys.exit(0)
"
