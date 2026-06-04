import asyncio
import time
import hmac
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Callable, Optional, Dict

logger = logging.getLogger("antimatter.scheduler")

RUNNING = False
SCHEDULER_HOOKS = []


def parse_cron(expression: str) -> Dict:
    parts = expression.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {expression}. Expected 5 fields (min hour day mon dow)")
    return {
        "minute": parts[0],
        "hour": parts[1],
        "day": parts[2],
        "month": parts[3],
        "day_of_week": parts[4],
    }


def _cron_match(field: str, value: int) -> bool:
    if field == "*":
        return True
    if "," in field:
        return any(_cron_match(p, value) for p in field.split(","))
    if "-" in field:
        low, high = field.split("-")
        return int(low) <= value <= int(high)
    if field.startswith("*/"):
        step = int(field[2:])
        return step > 0 and value % step == 0
    return int(field) == value


def check_cron(expression: str, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    try:
        cron = parse_cron(expression)
        return (
            _cron_match(cron["minute"], now.minute)
            and _cron_match(cron["hour"], now.hour)
            and _cron_match(cron["day"], now.day)
            and _cron_match(cron["month"], now.month)
            and _cron_match(cron["day_of_week"], now.weekday())
        )
    except Exception as e:
        logger.error(f"Cron check error: {e}")
        return False


def validate_webhook(payload: Dict, secret: str, signature: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        json.dumps(payload, sort_keys=True).encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


class Scheduler:
    def __init__(self, cron_expr: str = "0 8 * * *", max_hours: float = 2.0):
        self.cron_expr = cron_expr
        self.max_hours = max_hours
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._started_at: Optional[float] = None

    def register_hook(self, hook: Callable):
        SCHEDULER_HOOKS.append(hook)

    def _log_execution(self, trigger: str):
        import json
        from datetime import datetime, timezone
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"daily_execution_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.jsonl"
        entry = {"timestamp": time.time(), "trigger": trigger, "status": "completed"}
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    async def run_hooks(self, trigger: str):
        for hook in self.hooks:
            try:
                if callable(hook):
                    hook(trigger)
            except Exception as e:
                logger.error(f"Hook failed: {e}")
        self._log_execution(trigger)

    async def _loop(self):
        logger.info(f"Scheduler started with cron: {self.cron_expr}, max {self.max_hours}h per window")
        while self._running:
            now = datetime.now(timezone.utc)
            if self._started_at and (time.time() - self._started_at) > self.max_hours * 3600:
                logger.info("Max execution window reached. Entering idle.")
                self._started_at = None

            if self._started_at is None and check_cron(self.cron_expr, now):
                logger.info(f"Cron matched {self.cron_expr}. Starting execution window.")
                self._started_at = time.time()
                await self.run_hooks("cron")

            await asyncio.sleep(30)

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Scheduler started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Scheduler stopped")

    async def trigger_webhook(self, payload: Dict, secret: str, signature: str) -> bool:
        if not validate_webhook(payload, secret, signature):
            logger.warning("Invalid webhook signature")
            return False
        logger.info("Webhook validated. Starting execution.")
        self._started_at = time.time()
        await self.run_hooks("webhook")
        return True

    async def trigger_manual(self):
        logger.info("Manual trigger. Starting execution.")
        self._started_at = time.time()
        await self.run_hooks("manual")
