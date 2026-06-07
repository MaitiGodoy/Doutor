#!/usr/bin/env python3
"""Debug Hermes SSH command"""
import sys, json, base64
sys.path.insert(0, 'C:/Users/User/.gemini/antigravity-ide/scratch/doutor')
from kernel.hermes_bridge import VPS_SSH_KEY, VPS_USER, VPS_HOST, OLLAMA_BASE, OLLAMA_MODEL

payload = {"model": OLLAMA_MODEL, "prompt": "test prompt", "stream": False, "options": {"temperature": 0.3, "num_predict": 2048}}

script = """#!/usr/bin/env python3
import urllib.request, json, sys
data = %s
req = urllib.request.Request(
    "%s/api/generate",
    data=json.dumps(data).encode(),
    headers={"Content-Type": "application/json"}
)
try:
    resp = urllib.request.urlopen(req, timeout=120)
    print(resp.read().decode())
except Exception as e:
    print(json.dumps({"error": str(e)}), file=sys.stderr)
    sys.exit(1)
""" % (json.dumps(payload), OLLAMA_BASE)

script_b64 = base64.b64encode(script.encode()).decode()

cmd = (
    'ssh -i "' + VPS_SSH_KEY + '" -o StrictHostKeyChecking=no -o ConnectTimeout=10 '
    + VPS_USER + '@' + VPS_HOST + ' '
    + '"echo ' + script_b64 + ' | base64 -d | python3" 2>/dev/null'
)

print("=== CMD ===")
print(cmd[:300])
print()
print("=== Script first 120 ===")
print(script[:120])
print()
print("=== Testing bash on VPS ===")

import asyncio

async def test():
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    print("Return code:", proc.returncode)
    print("Stderr:", stderr.decode("utf-8", errors="replace")[:500])
    print("Stdout:", stdout.decode("utf-8", errors="replace")[:500])

asyncio.run(test())
