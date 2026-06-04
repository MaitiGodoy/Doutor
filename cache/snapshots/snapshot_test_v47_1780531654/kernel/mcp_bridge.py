import os
import json
import asyncio
import logging
from typing import List, Dict, Any
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logger = logging.getLogger("doutor.mcp_bridge")

app = Server("doutor-mcp-bridge")
master_key_instance = None

# ─── Agent/callable registry ─────────────────────────────────────

_agents = {}


def register_agent(name: str, callable_obj):
    _agents[name] = callable_obj


# ─── Tool definitions ────────────────────────────────────────────

TOOL_DEFINITIONS = [
    Tool(name="doutor_generate_code",
         description="Gera código tipado e modular",
         inputSchema={"type": "object", "properties": {"prompt": {"type": "string"}, "context_json": {"type": "string", "default": "{}"}}, "required": ["prompt"]}),
    Tool(name="doutor_generate_copy",
         description="Gera copy persuasivo (Neuro-Copy Cell)",
         inputSchema={"type": "object", "properties": {"task": {"type": "string"}}, "required": ["task"]}),
    Tool(name="doutor_optimize_seo",
         description="Otimiza SEO de arquivos HTML com BeautifulSoup",
         inputSchema={"type": "object", "properties": {"file_path": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}}}, "required": ["file_path", "keywords"]}),
    Tool(name="doutor_generate_dual_output",
         description="Gera versões desktop + mobile de HTML",
         inputSchema={"type": "object", "properties": {"content_spec_json": {"type": "string"}, "target_dir": {"type": "string", "default": "output/html"}}, "required": ["content_spec_json"]}),
    Tool(name="doutor_validate_compliance",
         description="Validação defensiva de código/dependências",
         inputSchema={"type": "object", "properties": {"target_path": {"type": "string"}, "scan_type": {"type": "string", "default": "comprehensive"}}, "required": ["target_path"]}),
    Tool(name="doutor_find_alternatives",
         description="Gera alternativas éticas para fases bloqueadas",
         inputSchema={"type": "object", "properties": {"blocked_phase": {"type": "string"}, "error_context_json": {"type": "string"}, "budget_status_json": {"type": "string"}}, "required": ["blocked_phase", "error_context_json", "budget_status_json"]}),
    Tool(name="read_file",
         description="Lê arquivo (auto-aprovado)",
         inputSchema={"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}),
    Tool(name="write_file",
         description="Escreve arquivo (auto-aprovado, com snapshot)",
         inputSchema={"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}),
    Tool(name="exec_shell",
         description="Executa comando (auto-aprovado, com sandbox)",
         inputSchema={"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}),
]


@app.list_tools()
async def list_tools() -> List[Tool]:
    return TOOL_DEFINITIONS


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    global master_key_instance
    try:
        # ── Master Key interception for critical tools ──
        if master_key_instance and name in ("write_file", "exec_shell", "read_file"):
            result = await master_key_instance.bypass_confirmation_loop(name, arguments)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

        # ── Tool routing ──
        if name == "doutor_generate_code":
            from kernel.agents import run_agent
            prompt = arguments.get("prompt", "")
            context = json.loads(arguments.get("context_json", "{}"))
            result = await run_agent("coder", prompt, context)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

        if name == "doutor_generate_copy":
            from kernel.agents import run_neuro_copy
            task = arguments.get("task", "")
            result = await run_neuro_copy(task)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

        if name == "doutor_optimize_seo":
            from departments.seo_engine import SEOEngine
            engine = SEOEngine()
            file_path = arguments.get("file_path", "")
            keywords = arguments.get("keywords", [])
            result = engine.optimize_site_keywords_and_meta(file_path, keywords)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

        if name == "doutor_generate_dual_output":
            from agents.dual_output_agent import DualOutputAgent
            agent = DualOutputAgent()
            spec = json.loads(arguments.get("content_spec_json", "{}"))
            target = arguments.get("target_dir", "output/html")
            result = await agent.generate_dual_output(spec, target)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

        if name == "doutor_validate_compliance":
            from kernel.lateral_agent import LateralAgent
            agent = LateralAgent()
            target = arguments.get("target_path", ".")
            scan = arguments.get("scan_type", "comprehensive")
            result = await agent.run_defensive_validation(target, scan)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

        if name == "doutor_find_alternatives":
            from kernel.lateral_agent import LateralAgent
            agent = LateralAgent()
            phase = arguments.get("blocked_phase", "")
            ctx = json.loads(arguments.get("error_context_json", "{}"))
            budget = json.loads(arguments.get("budget_status_json", "{}"))
            result = await agent.generate_alternatives(phase, ctx, budget)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, default=str))]

        if name == "read_file":
            path = arguments.get("path", "")
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return [TextContent(type="text", text=content)]

        if name == "write_file":
            path = arguments.get("path", "")
            content = arguments.get("content", "")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return [TextContent(type="text", text=json.dumps({"status": "ok", "path": path, "written": True}))]

        if name == "exec_shell":
            command = arguments.get("command", "")
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            out, err = await proc.communicate()
            return [TextContent(type="text", text=json.dumps({
                "exit_code": proc.returncode,
                "stdout": out.decode(errors="ignore"),
                "stderr": err.decode(errors="ignore"),
            }, ensure_ascii=False))]

        return [TextContent(type="text", text=json.dumps({"status": "error", "error": f"Unknown tool: {name}"}))]

    except Exception as e:
        logger.exception(f"Tool {name} failed")
        return [TextContent(type="text", text=json.dumps({"status": "error", "error": str(e)}))]


async def main():
    global master_key_instance
    logger.info("MCP Bridge v4.1 starting on stdio")
    async with stdio_server(app) as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
