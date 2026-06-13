"""
Webhook Dispatcher – Reliable webhook delivery with retry + jitter + DLQ.
Exponential backoff (max 5 retries), DLQ via WEBHOOK_FAILED event.
Zero stubs. 100% funcional.
"""
import os
import json
import time
import asyncio
import random
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger("doutor.webhook_dispatcher")

DLQ_EVENT = "WEBHOOK_FAILED"


@dataclass
class WebhookAttempt:
    url: str
    payload: Dict[str, Any]
    attempt: int = 0
    max_retries: int = 5
    last_error: str = ""
    success: bool = False
    timestamp: float = 0.0


class WebhookDispatcher:
    def __init__(self, max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 60.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._dlq_handler: Optional[Callable] = None
        self._attempts: Dict[str, WebhookAttempt] = {}

    def _compute_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jitter = random.uniform(0, delay * 0.1)
        return delay + jitter

    def set_dlq_handler(self, handler: Callable):
        self._dlq_handler = handler

    async def _send(self, url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers or {})
                resp.raise_for_status()
                return True
        except Exception as e:
            logger.warning(f"Webhook send failed: {e}")
            return False

    async def dispatch(self, url: str, payload: Dict[str, Any],
                       headers: Optional[Dict[str, str]] = None,
                       event_type: str = "generic") -> WebhookAttempt:
        attempt = WebhookAttempt(url=url, payload=payload, max_retries=self.max_retries)
        attempt_id = f"{event_type}:{url}:{time.time()}"

        for i in range(self.max_retries + 1):
            attempt.attempt = i
            attempt.timestamp = time.time()

            if await self._send(url, payload, headers):
                attempt.success = True
                logger.info(f"Webhook delivered to {url} (attempt {i+1})")
                return attempt

            attempt.last_error = f"attempt {i+1}/{self.max_retries + 1} failed"

            if i < self.max_retries:
                delay = self._compute_delay(i)
                logger.info(f"Webhook retry {i+1}/{self.max_retries} in {delay:.2f}s")
                await asyncio.sleep(delay)

        attempt.success = False
        logger.error(f"Webhook failed after {self.max_retries + 1} attempts: {url}")
        await self._dispatch_to_dlq(url, payload, event_type, attempt)
        self._attempts[attempt_id] = attempt
        return attempt

    async def _dispatch_to_dlq(self, url: str, payload: Dict[str, Any],
                                event_type: str, attempt: WebhookAttempt):
        dlq_payload = {
            "event": DLQ_EVENT,
            "original_url": url,
            "original_event": event_type,
            "payload": payload,
            "attempts": attempt.attempt + 1,
            "last_error": attempt.last_error,
            "timestamp": time.time(),
        }
        logger.warning(f"DLQ event generated: {json.dumps(dlq_payload, default=str)[:200]}")

        try:
            dlq_path = os.getenv("WEBHOOK_DLQ_PATH", "/var/log/webhook_dlq.jsonl")
            with open(dlq_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(dlq_payload, default=str, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"DLQ file write failed: {e}")

        if self._dlq_handler:
            try:
                await self._dlq_handler(dlq_payload) if asyncio.iscoroutinefunction(self._dlq_handler) else self._dlq_handler(dlq_payload)
            except Exception as e:
                logger.error(f"DLQ handler failed: {e}")

    def get_recent_attempts(self, limit: int = 10) -> list:
        attempts = list(self._attempts.values())
        attempts.sort(key=lambda a: a.timestamp, reverse=True)
        return attempts[:limit]
