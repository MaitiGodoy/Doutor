#!/usr/bin/env python3
"""Fix MCP server double braces"""
import sys, os

PATH = "/var/www/maiti-godoy-portal/doutor/kernel/mcp_server.py"
BAK = PATH + ".bak3"

with open(PATH) as f:
    c = f.read()

# Backup
open(BAK, "w").write(c)

# Fix double braces in handler functions
c = c.replace('{{"status": "ok", "hermes": "ask received", "task": args.get("task","")}}', 
              '{"status": "ok", "hermes": "ask received", "task": args.get("task","")}')
c = c.replace('{{"status": "ok", "hermes": "v0.15.1", "model": "hermes3:8b"}}',
              '{"status": "ok", "hermes": "v0.15.1", "model": "hermes3:8b"}')

# Add tool definitions after the first _build_tool entry
HERMES_TOOLS = '''    _build_tool(
        "doutor_hermes_ask",
        "Delega tarefa ao Hermes Agent v0.15.1 na VPS",
        properties={
            "task": {"type": "string", "description": "Tarefa para o Hermes"},
            "context": {"type": "string", "description": "Contexto opcional"}
        },
        required=["task"]
    ),
    _build_tool(
        "doutor_hermes_status",
        "Status do Hermes Agent (conexao, modelo, calls)",
        properties={}
    ),
'''

if "doutor_hermes_ask" not in c.split("_TOOL_HANDLERS")[0]:
    idx = c.index("_build_tool(")
    first_close = c.index("),\n    _build_tool(", idx)
    c = c[:first_close+1] + "\n" + HERMES_TOOLS + c[first_close+1:]
    print("Tool definitions: ADDED")
else:
    print("Tool definitions: ALREADY EXISTS")

with open(PATH, "w") as f:
    f.write(c)

print("Done")
