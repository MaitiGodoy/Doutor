#!/usr/bin/env python3
"""Add Hermes tool definitons + handler functions to VPS mcp_server.py"""
import re

PATH = "/var/www/maiti-godoy-portal/doutor/kernel/mcp_server.py"

with open(PATH) as f:
    content = f.read()

changes = 0

# 1. Add tool definitions
hermes_tools = '''
    _build_tool(
        "doutor_hermes_ask",
        "Delega uma tarefa ao Hermes Agent (v0.15.1) na VPS",
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

if "doutor_hermes_ask" not in content:
    # Insert after the first _build_tool entry
    pattern = '_build_tool(\n        "doutor_status"'
    idx = content.find(pattern)
    if idx > 0:
        # Find end of first tool definition (closing paren + comma)
        first_tool_end = content.find("),\n    _build_tool(", idx)
        if first_tool_end > 0:
            content = content[:first_tool_end+1] + hermes_tools + content[first_tool_end+1:]
            changes += 1
            print("Tool definitions added")

# 2. Add handler functions
hermes_funcs = """

async def _handle_hermes_ask(args: dict) -> dict:
    \"\"\"doutor_hermes_ask: delega ao Hermes Agent\"\"\"
    orch = await _get_orchestrator()
    if hasattr(orch, "hermes"):
        return await orch.hermes.participate_execution(
            args.get("task", ""),
            {"context": args.get("context", "")}
        )
    return {"status": "error", "error": "HermesBridge not initialized"}


async def _handle_hermes_status(args: dict) -> dict:
    \"\"\"doutor_hermes_status: status do Hermes Agent\"\"\"
    orch = await _get_orchestrator()
    if hasattr(orch, "hermes"):
        stats = orch.hermes.get_stats()
        status = await orch.hermes.get_status()
        return {"stats": stats, "status": status}
    return {"status": "error", "error": "HermesBridge not initialized"}
"""

if "_handle_hermes_ask" not in content:
    idx = content.find("_TOOL_HANDLERS = {")
    if idx > 0:
        content = content[:idx] + hermes_funcs + "\n" + content[idx:]
        changes += 1
        print("Handler functions added")

if changes > 0:
    with open(PATH, "w") as f:
        f.write(content)
    print(f"Done! {changes} patch(es) applied.")
else:
    print("No changes needed - already patched.")
