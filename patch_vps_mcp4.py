#!/usr/bin/env python3
"""Fix Hermes MCP handlers and add tool definitions"""
import os

PATH = "/var/www/maiti-godoy-portal/doutor/kernel/mcp_server.py"

with open(PATH) as f:
    content = f.read()

# Fix the handler functions (replace {{ with { and }} with })
content = content.replace(
    '    return {{"status": "ok", "hermes": "ask received", "task": args.get("task","")}}',
    '    return {"status": "ok", "hermes": "ask received", "task": args.get("task","")}'
)
content = content.replace(
    '    return {{"status": "ok", "hermes": "v0.15.1", "model": "hermes3:8b"}}',
    '    return {"status": "ok", "hermes": "v0.15.1", "model": "hermes3:8b"}'
)

# Add tool definitions if missing
if "doutor_hermes_ask" not in content.split("_TOOL_HANDLERS")[0]:
    # Find the position right after the first _build_tool(... ), pattern
    idx = content.index("_build_tool(")
    first_close = content.index("),\n    _build_tool(", idx)
    
    hermes_tools = """    _build_tool(
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
"""
    content = content[:first_close+1] + hermes_tools + content[first_close+1:]
    print("Tool definitions added")

with open(PATH, "w") as f:
    f.write(content)

# Verify
with open(PATH) as f:
    c = f.read()
    ask_count = c.count("doutor_hermes_ask")
    func_count = c.count("async def _handle_hermes_ask")
    print(f"Verification: doutor_hermes_ask refs={ask_count}, funcs={func_count}")
    print("MCP server patched successfully!")
