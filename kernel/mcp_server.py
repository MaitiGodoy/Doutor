"""
MCP Server – Exposes Doutor Antimatter kernel tools via Model Context Protocol.
Communicates over stdio (JSON-RPC). Zero stubs.
"""
import os, sys, json, asyncio, logging
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("mcp_server")

try:
    from mcp.server import FastMCP
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    logger.error("mcp package required: pip install mcp")
    sys.exit(1)

from kernel.provider_router import get_provider_router
from kernel.circuit_breaker import CircuitBreaker, CircuitState
from gateway.api_gateway import ApiGateway

mcp = FastMCP("doutor")

api_gateway = ApiGateway()


@mcp.tool()
async def doutor_health() -> str:
    """Check Doutor kernel health status."""
    result = await api_gateway.health({"chain_id": "mcp-health"})
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def doutor_execute(user_input: str, module: str = "multi",
                          priority: str = "normal") -> str:
    """Execute a task through Doutor's orchestrator pipeline.
    
    Args:
        user_input: The task description or prompt to execute.
        module: Execution module (programming, marketing, infoproduct, multi).
        priority: Task priority (low, normal, high, critical).
    """
    result = await api_gateway.execute({
        "user_input": user_input,
        "module": module,
        "priority": priority,
    })
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def doutor_providers() -> str:
    """List available LLM providers and their circuit breaker status."""
    router = get_provider_router()
    statuses = []
    for name, breaker in router.breakers.items():
        statuses.append({
            "provider": name,
            "state": breaker.state.value,
            "failures": breaker.failures,
            "failure_threshold": breaker.failure_threshold,
        })
    return json.dumps(statuses, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="stdio")
