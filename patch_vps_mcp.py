#!/usr/bin/env python3
"""Patch VPS mcp_server.py to add Hermes tools"""
import re

VPS_PATH = "/var/www/maiti-godoy-portal/doutor/kernel/mcp_server.py"

with open(VPS_PATH) as f:
    content = f.read()

# Patch 1: Add Hermes tool definition after the first tool definition
hermes_tool_def = '''
    _build_tool(
        "doutor_hermes_ask",
        "Delega uma tarefa ao Hermes Agent (v0.15.1) na VPS. Hermes participa de todas as etapas do pipeline Doutor.",
        properties={
            "task": {
                "type": "string",
                "description": "Tarefa ou pergunta para o Hermes Agent"
            },
            "context": {
                "type": "string",
                "description": "Contexto adicional para o Hermes (opcional)"
            }
        },
        required=["task"]
    ),
    _build_tool(
        "doutor_hermes_status",
        "Retorna status do Hermes Agent (conexao, modelo, calls)",
        properties={}
    ),
'''

insert_point = content.find('_build_tool("doutor_status"')
if insert_point > 0 and "doutor_hermes_ask" not in content:
    # Insert after the opening bracket of _TOOL_DEFINITIONS
    bracket_end = content.find("[", content.find("_TOOL_DEFINITIONS"))
    if bracket_end > 0:
        content = content[:bracket_end+1] + "\n" + hermes_tool_def + content[bracket_end+1:]
        print("Patch 1: Hermes tool definitions added")

# Patch 2: Add Hermes handlers
hermes_handlers = '''
    "doutor_hermes_ask": _handle_hermes_ask,
    "doutor_hermes_status": _handle_hermes_status,
'''
handlers_end = content.find("_TOOL_HANDLERS = {")
if handlers_end > 0 and "doutor_hermes_ask" not in content:
    brace_end = content.find("{", handlers_end)
    if brace_end > 0:
        content = content[:brace_end+1] + hermes_handlers + content[brace_end+1:]
        print("Patch 2: Hermes handlers added")

# Patch 3: Add Hermes handler functions before the handlers dict
hermes_functions = '''
async def _handle_hermes_ask(args: dict) -> dict:
    """doutor_hermes_ask: delega tarefa ao Hermes Agent"""
    orch = await _get_orchestrator()
    task = args.get("task", "")
    context = args.get("context", "")
    if hasattr(orch, "hermes"):
        result = await orch.hermes.participate_execution(task, {"context": context})
        return result
    return {"status": "error", "error": "HermesBridge not initialized"}


async def _handle_hermes_status(args: dict) -> dict:
    """doutor_hermes_status: status do Hermes Agent"""
    orch = await _get_orchestrator()
    if hasattr(orch, "hermes"):
        stats = orch.hermes.get_stats()
        status = await orch.hermes.get_status()
        return {"stats": stats, "status": status}
    return {"status": "error", "error": "HermesBridge not initialized"}

'''
# Insert before _TOOL_HANDLERS
insert_before = "_TOOL_HANDLERS = {"
if "doutor_hermes_ask" not in content:
    idx = content.find(insert_before)
    if idx > 0:
        content = content[:idx] + "\n\n" + hermes_functions + "\n" + content[idx:]
        print("Patch 3: Hermes handler functions added")

with open(VPS_PATH, "w") as f:
    f.write(content)
print("MCP server patched successfully!")
