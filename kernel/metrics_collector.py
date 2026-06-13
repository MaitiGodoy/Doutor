"""
Metrics Collector — Telemetria OpenTelemetry para o Doutor v5.1.

Coleta métricas de tarefas com chain_id, latência, tokens, eventos.
Exporta para logs/metrics.jsonl em formato JSONL.
Integrado com provider_router para capturar chamadas LLM.
Zero dependências externas. Python stdlib.
"""

import json
import time
import asyncio
import os
from pathlib import Path
from collections import defaultdict
from typing import Optional


class MetricsCollector:
    """Coletor de métricas para telemetria OpenTelemetry.

    Fornece:
    - start_chain / end_chain para medir latência de tarefas
    - record_llm_call para capturar uso de tokens por provider
    - Exportação JSONL para logs/metrics.jsonl
    """

    def __init__(self, log_path: str = "logs/metrics.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._chains: dict[str, dict] = {}
        self._llm_calls: list[dict] = []
        self._event_buffer: list[dict] = []
        self._flush_interval = 30
        self._total_tokens_in = 0
        self._total_tokens_out = 0

    # ─── Chain Management ─────────────────────────────────────

    def start_chain(self, task_id: str) -> str:
        """Inicia uma chain de telemetria para uma tarefa.

        Args:
            task_id: Identificador único da tarefa.

        Returns:
            chain_id string.
        """
        chain_id = f"chain_{task_id}_{int(time.time())}"
        self._chains[chain_id] = {
            "chain_id": chain_id,
            "task_id": task_id,
            "start_time": time.time(),
            "end_time": None,
            "latency_ms": None,
            "events": [],
            "llm_calls": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "status": "running",
        }
        self._emit_event(chain_id, "chain_started", {"task_id": task_id})
        return chain_id

    def end_chain(self, chain_id: str, status: str = "completed") -> dict:
        """Finaliza uma chain e calcula latência.

        Args:
            chain_id: ID da chain a finalizar.
            status: status final (completed, failed, cancelled).

        Returns:
            Dict com métricas da chain.
        """
        chain = self._chains.get(chain_id)
        if not chain:
            return {"error": f"Chain {chain_id} not found"}

        chain["end_time"] = time.time()
        chain["latency_ms"] = round((chain["end_time"] - chain["start_time"]) * 1000, 2)
        chain["status"] = status

        self._emit_event(chain_id, "chain_ended", {
            "latency_ms": chain["latency_ms"],
            "status": status,
            "llm_calls": chain["llm_calls"],
            "tokens_in": chain["tokens_in"],
            "tokens_out": chain["tokens_out"],
            "total_events": len(chain["events"]),
        })

        self._flush()
        return self.get_chain_metrics(chain_id)

    def get_active_chains(self) -> list[dict]:
        """Retorna todas as chains em execução."""
        return [c for c in self._chains.values() if c["status"] == "running"]

    def get_chain_metrics(self, chain_id: str) -> Optional[dict]:
        """Retorna métricas completas de uma chain."""
        chain = self._chains.get(chain_id)
        if not chain:
            return None

        return {
            "chain_id": chain["chain_id"],
            "task_id": chain["task_id"],
            "latency_ms": chain["latency_ms"],
            "status": chain["status"],
            "llm_calls": chain["llm_calls"],
            "tokens_in": chain["tokens_in"],
            "tokens_out": chain["tokens_out"],
            "total_events": len(chain["events"]),
            "start_time": chain["start_time"],
            "end_time": chain["end_time"],
            "age_seconds": round(time.time() - chain["start_time"], 2) if chain["end_time"] is None else None,
        }

    def chain_add_event(self, chain_id: str, event_type: str, data: dict = None):
        """Adiciona evento customizado a uma chain."""
        chain = self._chains.get(chain_id)
        if not chain:
            return
        event = {
            "event_type": event_type,
            "data": data or {},
            "timestamp": time.time(),
        }
        chain["events"].append(event)
        self._emit_event(chain_id, event_type, data or {})

    # ─── LLM Call Recording ───────────────────────────────────

    def record_llm_call(
        self,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        latency_ms: float,
        chain_id: str = None,
        status: str = "success",
    ) -> dict:
        """Registra chamada LLM com métricas de consumo.

        Args:
            provider: Nome do provider (openai, anthropic, ollama, etc).
            model: Nome do modelo usado.
            tokens_in: Tokens de input.
            tokens_out: Tokens de output.
            latency_ms: Latência da chamada em ms.
            chain_id: Chain associada (opcional).
            status: status da chamada (success, error, timeout).

        Returns:
            Dict com o registro criado.
        """
        record = {
            "provider": provider,
            "model": model,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tokens_total": tokens_in + tokens_out,
            "latency_ms": round(latency_ms, 2),
            "chain_id": chain_id,
            "status": status,
            "timestamp": time.time(),
        }

        self._llm_calls.append(record)
        self._total_tokens_in += tokens_in
        self._total_tokens_out += tokens_out

        # Vincula à chain se existir
        if chain_id and chain_id in self._chains:
            chain = self._chains[chain_id]
            chain["llm_calls"] += 1
            chain["tokens_in"] += tokens_in
            chain["tokens_out"] += tokens_out

        self._emit_event(
            chain_id or "no_chain",
            "llm_call",
            {
                "provider": provider,
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "latency_ms": round(latency_ms, 2),
                "status": status,
            },
        )

        return record

    def get_llm_stats(self, provider: str = None) -> dict:
        """Estatísticas agregadas de chamadas LLM.

        Args:
            provider: Filtrar por provider específico.

        Returns:
            Dict com métricas agregadas.
        """
        calls = self._llm_calls
        if provider:
            calls = [c for c in calls if c["provider"] == provider]

        if not calls:
            return {
                "total_calls": 0,
                "total_tokens_in": 0,
                "total_tokens_out": 0,
                "avg_latency_ms": 0,
                "error_rate": 0,
            }

        total = len(calls)
        errors = sum(1 for c in calls if c["status"] != "success")
        latencies = [c["latency_ms"] for c in calls if c["status"] == "success"]

        return {
            "total_calls": total,
            "total_tokens_in": sum(c["tokens_in"] for c in calls),
            "total_tokens_out": sum(c["tokens_out"] for c in calls),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0,
            "error_rate": round(errors / total, 4),
            "error_count": errors,
        }

    def get_provider_breakdown(self) -> dict:
        """Breakdown de uso por provider."""
        breakdown = {}
        for call in self._llm_calls:
            prov = call["provider"]
            if prov not in breakdown:
                breakdown[prov] = {
                    "calls": 0,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "latency_sum": 0,
                    "errors": 0,
                }
            breakdown[prov]["calls"] += 1
            breakdown[prov]["tokens_in"] += call["tokens_in"]
            breakdown[prov]["tokens_out"] += call["tokens_out"]
            breakdown[prov]["latency_sum"] += call["latency_ms"]
            if call["status"] != "success":
                breakdown[prov]["errors"] += 1

        for prov, data in breakdown.items():
            if data["calls"] > 0:
                data["avg_latency_ms"] = round(data["latency_sum"] / data["calls"], 2)
                data["tokens_total"] = data["tokens_in"] + data["tokens_out"]
            del data["latency_sum"]

        return breakdown

    # ─── Event Buffer & Export ────────────────────────────────

    def _emit_event(self, chain_id: str, event_type: str, data: dict):
        """Bufferiza evento para exportação."""
        self._event_buffer.append({
            "chain_id": chain_id,
            "event_type": event_type,
            "data": data,
            "timestamp": time.time(),
        })

    def _flush(self):
        """Descarrega buffer em logs/metrics.jsonl."""
        if not self._event_buffer:
            return
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                for event in self._event_buffer:
                    f.write(json.dumps(event, ensure_ascii=False) + "\n")
            self._event_buffer.clear()
        except OSError:
            pass

    def flush(self):
        """Força flush do buffer."""
        self._flush()

    # ─── Snapshot & Reset ─────────────────────────────────────

    def snapshot(self) -> dict:
        """Snapshot completo do estado atual das métricas.

        Returns:
            Dict com todas as métricas do sistema.
        """
        self._flush()
        return {
            "chains": {
                "active": len(self.get_active_chains()),
                "total_started": len(self._chains),
                "active_details": [self.get_chain_metrics(c["chain_id"]) for c in self.get_active_chains()],
            },
            "llm": {
                "total_calls": len(self._llm_calls),
                "total_tokens_in": self._total_tokens_in,
                "total_tokens_out": self._total_tokens_out,
                "provider_breakdown": self.get_provider_breakdown(),
            },
            "log_path": str(self.log_path),
            "log_size_bytes": self.log_path.stat().st_size if self.log_path.exists() else 0,
            "timestamp": time.time(),
        }

    def reset(self):
        """Reseta todas as métricas (útil para novos ciclos)."""
        self._chains.clear()
        self._llm_calls.clear()
        self._event_buffer.clear()
        self._total_tokens_in = 0
        self._total_tokens_out = 0

    # ─── Provider Router Integration ──────────────────────────

    @staticmethod
    def wrap_provider_call(collector, chain_id: str, provider: str, model: str):
        """Decorator para capturar métricas de chamadas LLM via provider_router.

        Uso:
            collector = MetricsCollector()
            wrapped_fn = MetricsCollector.wrap_provider_call(
                collector, chain_id, "anthropic", "claude-sonnet-4-6"
            )(original_fn)
            result = await wrapped_fn(prompt, **kwargs)
        """
        def decorator(func):
            async def wrapper(*args, **kwargs):
                start = time.time()
                try:
                    result = await func(*args, **kwargs)
                    latency = (time.time() - start) * 1000
                    tokens_in = len(str(kwargs.get("prompt", args[0] if args else ""))) // 4
                    tokens_out = len(str(result)) // 4
                    collector.record_llm_call(
                        provider=provider,
                        model=model,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        latency_ms=latency,
                        chain_id=chain_id,
                        status="success",
                    )
                    return result
                except Exception as e:
                    latency = (time.time() - start) * 1000
                    collector.record_llm_call(
                        provider=provider,
                        model=model,
                        tokens_in=0,
                        tokens_out=0,
                        latency_ms=latency,
                        chain_id=chain_id,
                        status="error",
                    )
                    raise
            return wrapper
        return decorator
