import sys
import os
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'

import json
import asyncio
import logging
import uuid
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("doutor.main")

from kernel.orchestrator import AntimatterOrchestrator as Orchestrator
from kernel.scheduler import Scheduler
from kernel.health import health_status, auto_recover
from kernel.state_manager import StateManager
from kernel.budget_dashboard import generate_dashboard
from kernel.config import PRODUCTION
from kernel.provider_quotas import circuit_breaker_status


def ensure_dirs():
    for d in ["data", "logs", "output", "sandbox", "cache"]:
        os.makedirs(d, exist_ok=True)


async def run_pipeline(input_data: dict) -> dict:
    orch = Orchestrator(input_data)
    result = await orch.run_with_concierge()
    return result


async def manual_mode(input_file: str = None):
    input_data = {
        "type": "infoproduct",
        "niche": "Productivity for Developers",
        "audience": "Remote Engineers 25-40",
        "goal": "Waitlist + Pre-sale",
        "platforms": ["LinkedIn", "Twitter", "Email"],
        "tone": "Technical but accessible",
        "budget_limit": 0,
        "kpis": ["ctr", "conversion_rate"]
    }
    if input_file:
        with open(input_file, "r", encoding="utf-8") as f:
            input_data = json.load(f)

    result = await run_pipeline(input_data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


async def webhook_mode(host: str = "0.0.0.0", port: int = 8080):
    from aiohttp import web

    async def handle_webhook(request):
        from kernel.scheduler import validate_webhook
        body = await request.json()
        signature = request.headers.get("X-Signature", "")
        secret = PRODUCTION.get("webhook_secret", "change-me")

        if not validate_webhook(body, secret, signature):
            return web.json_response({"status": "error", "message": "Invalid signature"}, status=401)

        run_id = body.get("run_id", f"wh_{uuid.uuid4().hex[:12]}")
        logger.info(f"Webhook received: run_id={run_id}")

        asyncio.create_task(run_pipeline({**body, "run_id": run_id}))

        return web.json_response({
            "status": "accepted",
            "run_id": run_id,
            "message": "Pipeline triggered via webhook",
        })

    async def handle_health(request):
        health = health_status()
        return web.json_response(health)

    async def handle_quotas(request):
        from kernel.provider_quotas import get_all_quotas
        return web.json_response({"quotas": get_all_quotas()})

    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/quotas", handle_quotas)

    logger.info(f"Webhook server starting on {host}:{port}")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    await asyncio.Event().wait()


async def cron_mode():
    cron_schedule = PRODUCTION.get("cron_schedule", "0 8 * * *")
    max_hours = PRODUCTION.get("max_daily_run_hours", 2.0)

    scheduler = Scheduler(cron_expr=cron_schedule, max_hours=max_hours)

    async def pipeline_hook(trigger: str):
        logger.info(f"Triggered ({trigger}). Starting daily pipeline.")
        try:
            result = await run_pipeline({"trigger": trigger})
            if PRODUCTION.get("generate_dashboard"):
                generate_dashboard()
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")

    scheduler.register_hook(pipeline_hook)
    scheduler.start()

    logger.info(f"Cron mode active. Schedule: {cron_schedule}, max {max_hours}h/day")
    logger.info("Waiting for scheduled trigger or Ctrl+C...")

    try:
        while True:
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        await scheduler.stop()


async def dashboard_mode():
    path = generate_dashboard()
    print(f"Dashboard generated: {os.path.abspath(path)}")


async def main():
    ensure_dirs()
    sm = StateManager()
    sm.init_db()

    # Auto-recover DB if corrupted
    auto_recover()

    # Check circuit breaker status on startup
    circuit = circuit_breaker_status()
    logger.info(f"Circuit breaker: {circuit.get('healthy_count')}/{circuit.get('total_providers')} providers healthy")

    if circuit.get("all_blocked"):
        logger.warning("ALL PROVIDERS BLOCKED. System will run in low-power mode (cache only).")

    mode = "manual"
    arg = None

    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if len(sys.argv) > 2:
            arg = sys.argv[2]

    if mode == "manual" or mode == "m":
        await manual_mode(arg)
    elif mode == "webhook" or mode == "w":
        port = int(arg) if arg else 8080
        await webhook_mode(port=port)
    elif mode == "cron" or mode == "c":
        await cron_mode()
    elif mode == "health" or mode == "h":
        health = health_status()
        print(json.dumps(health, indent=2))
    elif mode == "quotas" or mode == "q":
        from kernel.provider_quotas import get_all_quotas
        print(json.dumps({"quotas": get_all_quotas()}, indent=2))
    elif mode == "reset" or mode == "r":
        from kernel.token_manager import TokenManager
        tm = TokenManager()
        tm.reset_daily_quotas()
        print("Daily quotas reset.")
    elif mode == "dashboard" or mode == "d":
        await dashboard_mode()
    elif mode == "backup":
        path = sm.daily_backup()
        print(f"Backup created: {path}")
    elif mode == "start" or mode == "s":
        import subprocess
        print("[Doutor] Verificando integridade antes do push...")
        result = subprocess.run(["python", "-c", """
import asyncio, sys
sys.path.insert(0, '.')
from agents.warden_agent import WardenAgent
wa = WardenAgent({'role': 'the_warden', 'max_retries': 0, 'timeout': 30}, None)
r = asyncio.run(wa.pre_execution_check())
sys.exit(0 if r['status'] == 'approved' else 1)
"""], capture_output=True, text=True)
        if result.returncode != 0:
            print("[Doutor] WARDEN BLOQUEOU: degradacao detectada. Corrija antes do push.")
            print(result.stderr)
            sys.exit(1)
        print("[Doutor] Warden aprovou. Commitando mudancas...")
        r = subprocess.run(["git", "add", "-A"], capture_output=True, text=True)
        r = subprocess.run(["git", "commit", "-m", f"auto-sync {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"], capture_output=True, text=True)
        if r.returncode != 0 and "nothing to commit" not in r.stdout and "nothing to commit" not in r.stderr:
            print(f"  commit: {r.stdout.strip()[:200]} {r.stderr.strip()[:200]}")
        print("[Doutor] Subindo para GitHub...")
        r = subprocess.run(["git", "push", "origin", "main"], capture_output=True, text=True)
        if r.returncode == 0:
            print("[Doutor] GitHub atualizado com sucesso.")
            print(f"  {r.stdout.strip()}")
        else:
            print(f"[Doutor] ERRO no push: {r.stderr.strip()}")
            sys.exit(1)
    else:
        print(f"Usage: python main.py [mode] [args]")
        print(f"Modes: manual (m) [input.json] | webhook (w) [port] | cron (c) | health (h) | quotas (q) | reset (r) | dashboard (d) | backup | start (s)")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
