#!/usr/bin/env python3
"""
Hermes MCP Bridge — Doutor v5.0
Proxy MCP local que tunela para `hermes mcp serve` na VPS via SSH.
Permite que opencode se conecte diretamente ao Hermes Agent sem
expor portas na VPS.
"""
import asyncio
import json
import logging
import os
import sys
import subprocess

logging.basicConfig(
    level=logging.INFO,
    format="[HERMES-BRIDGE] %(levelname)s %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("hermes_bridge")

# Configurações da VPS
VPS_HOST = "2.24.71.246"
VPS_USER = "root"
VPS_SSH_KEY = os.path.expanduser("~/.ssh/hostinger_vps.pem")

async def bridge():
    """
    Abre um túnel SSH e conecta stdin/stdout local ao
    `docker exec hermes hermes mcp serve --accept-hooks` na VPS.
    """
    ssh_cmd = [
        "ssh",
        "-i", VPS_SSH_KEY,
        "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=10",
        "-o", "ServerAliveInterval=30",
        "-o", "ServerAliveCountMax=3",
        f"{VPS_USER}@{VPS_HOST}",
        "docker exec -i hermes hermes mcp serve --accept-hooks 2>/dev/null"
    ]

    logger.info(f"Conectando ao Hermes Agent na VPS ({VPS_HOST})...")

    try:
        proc = await asyncio.create_subprocess_exec(
            *ssh_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
    except Exception as e:
        logger.error(f"Falha ao iniciar subprocesso SSH: {e}")
        sys.exit(1)

    async def forward_stdin():
        """Lê do stdin local e escreve no stdin do processo SSH."""
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while True:
            try:
                data = await reader.read(65536)
                if not data:
                    break
                if proc.stdin and not proc.stdin.is_closing():
                    proc.stdin.write(data)
                    await proc.stdin.drain()
            except Exception:
                break

        if proc.stdin and not proc.stdin.is_closing():
            proc.stdin.close()

    async def forward_stdout():
        """Lê do stdout do SSH e escreve no stdout local."""
        while True:
            try:
                line = await asyncio.wait_for(proc.stdout.readline(), timeout=0.5)
                if not line:
                    break
                # Escreve raw no stdout (MCP usa JSON-RPC)
                sys.stdout.buffer.write(line)
                sys.stdout.buffer.flush()
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    async def forward_stderr():
        """Lê do stderr do SSH e loga."""
        while True:
            try:
                line = await asyncio.wait_for(proc.stderr.readline(), timeout=0.5)
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").strip()
                if decoded:
                    logger.info(f"[VPS] {decoded}")
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    logger.info("Bridge MCP Hermes estabelecida. Tunelando stdin/stdout...")

    # Executa os forwards concorrentemente
    await asyncio.gather(
        forward_stdin(),
        forward_stdout(),
        forward_stderr()
    )

    exit_code = await proc.wait()
    logger.info(f"Conexão SSH encerrada (exit code: {exit_code})")
    sys.exit(exit_code)


if __name__ == "__main__":
    if not os.path.exists(VPS_SSH_KEY):
        logger.error(f"Chave SSH não encontrada: {VPS_SSH_KEY}")
        sys.exit(1)
    asyncio.run(bridge())
