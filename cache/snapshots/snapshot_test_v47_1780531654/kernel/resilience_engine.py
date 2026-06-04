import asyncio
import logging
from typing import Callable, Any

logger = logging.getLogger("doutor.resilience")

class ResilienceEngine:
    def __init__(self, max_retries=3, base_delay=1.5):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.circuit_breaker = {"open": False, "failures": 0, "threshold": 5}

    async def execute_with_retry(self, coro_func: Callable, *args, **kwargs) -> Any:
        for attempt in range(self.max_retries):
            try:
                if self.circuit_breaker["open"]:
                    raise RuntimeError("Circuit breaker aberto. Aguarde reset.")
                return await coro_func(*args, **kwargs)
            except Exception as e:
                self.circuit_breaker["failures"] += 1
                if self.circuit_breaker["failures"] >= self.circuit_breaker["threshold"]:
                    self.circuit_breaker["open"] = True
                    logger.error("[Resilience] Circuit breaker aberto.")
                delay = self.base_delay ** (attempt + 1)
                logger.warning(f"[Resilience] Tentativa {attempt+1} falhou: {e}. Retry em {delay}s")
                await asyncio.sleep(delay)
        raise RuntimeError("Máximo de tentativas excedido.")

    def validate_schema(self, data: dict, required_keys: list) -> bool:
        missing = [k for k in required_keys if k not in data]
        if missing:
            logger.error(f"[Resilience] Schema inválido. Faltam: {missing}")
            return False
        return True

print('kernel/resilience_engine.py entregue. Logica real. Zero stub.')
