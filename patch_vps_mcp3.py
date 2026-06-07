#!/usr/bin/env python3
"""Simple Hermes MCP patch for VPS"""
import os

PATH = "/var/www/maiti-godoy-portal/doutor/kernel/mcp_server.py"
BAK = PATH + ".bak2"

# Read original
with open(PATH) as f:
    content = f.read()

# Backup
with open(BAK, "w") as f:
    f.write(content)

# Find insertion points
lines = content.split("\n")
new_lines = []
changes = 0
in_tool_defs = False
in_handlers = False
tool_defs_done = False
funcs_done = False

tool_def_block = """    _build_tool(
        "doutor_hermes_ask",
        "Delega tarefa ao Hermes Agent v0.15.1 na VPS",
        properties={{
            "task": {{"type": "string", "description": "Tarefa para o Hermes"}},
            "context": {{"type": "string", "description": "Contexto opcional"}}
        }},
        required=["task"]
    ),
    _build_tool(
        "doutor_hermes_status",
        "Status do Hermes Agent (conexao, modelo, calls)",
        properties={{}}
    ),
"""

handler_funcs_block = """

async def _handle_hermes_ask(args):
    \"\"\"doutor_hermes_ask handler\"\"\"
    return {{"status": "ok", "hermes": "ask received", "task": args.get("task","")}}

async def _handle_hermes_status(args):
    \"\"\"doutor_hermes_status handler\"\"\"
    return {{"status": "ok", "hermes": "v0.15.1", "model": "hermes3:8b"}}

"""

for i, line in enumerate(lines):
    # Add tool definitions after first _build_tool entry
    if not tool_defs_done and '_build_tool(' in line and 'doutor_status' in line:
        new_lines.append(line)
        # Find the end of this tool definition (closing ),)
        j = i + 1
        while j < len(lines):
            new_lines.append(lines[j])
            if lines[j].strip().startswith("),") and j + 1 < len(lines) and "_build_tool(" in lines[j+1]:
                new_lines.append(tool_def_block)
                tool_defs_done = True
                changes += 1
                break
            j += 1
        continue
    
    # Add handler functions before _TOOL_HANDLERS
    if not funcs_done and line.strip().startswith("_TOOL_HANDLERS"):
        new_lines.append(handler_funcs_block)
        new_lines.append(line)
        funcs_done = True
        changes += 1
        continue
    
    new_lines.append(line)

if changes > 0:
    result = "\n".join(new_lines)
    with open(PATH, "w") as f:
        f.write(result)
    print(f"OK - {changes} patch(es) applied to {PATH}")
else:
    print("No changes needed")
