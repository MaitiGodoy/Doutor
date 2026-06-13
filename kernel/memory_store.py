"""
Memory Store — Event Sourcing + CQRS para o Doutor v5.

SQLite WAL mode para logs de eventos, projeções assíncronas,
read models em memória. aiosqlite para segurança async.
"""

import aiosqlite
import json
import asyncio
import os
import time
import uuid
from pathlib import Path
from collections import defaultdict
from typing import Optional


class MemoryStore:
    """Armazenamento de memória com padrão Event Sourcing + CQRS.

    Eventos são append-only em SQLite WAL mode.
    Projeções são read models atualizados assincronamente.
    """

    def __init__(self, db_path: str = "data/memory_store.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._projections: dict[str, asyncio.Task] = {}
        self._read_models: dict[str, dict] = {}
        self._event_log_path: Optional[Path] = None
        self._db_ready: bool = False
        self._init_event_log()

    async def _ensure_db(self):
        if not self._db_ready:
            await self._init_db()
            self._db_ready = True

    async def _init_db(self):
        """Inicializa SQLite com WAL mode."""
        async with aiosqlite.connect(str(self.db_path)) as conn:
            await conn.execute("PRAGMA journal_mode=WAL;")
            await conn.execute("PRAGMA synchronous=NORMAL;")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    aggregate_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1
                )
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_aggregate
                ON events(aggregate_id)
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_type
                ON events(event_type)
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    aggregate_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            await conn.commit()

    def _init_event_log(self):
        """Garante diretório para log de eventos JSON."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        self._event_log_path = log_dir / "events.jsonl"

    async def append_event(self, event: dict) -> str:
        """Appenda evento ao store. Retorna ID do evento."""
        await self._ensure_db()
        event_id = str(uuid.uuid4())
        timestamp = time.time()
        version = await self._next_version(event.get("aggregate_id", ""))

        row = (
            event_id,
            event.get("aggregate_id", ""),
            event.get("event_type", "unknown"),
            json.dumps(event.get("data", {}), ensure_ascii=False),
            timestamp,
            version,
        )

        async with aiosqlite.connect(str(self.db_path)) as conn:
            await conn.execute(
                "INSERT INTO events (id, aggregate_id, event_type, data, timestamp, version) VALUES (?, ?, ?, ?, ?, ?)",
                row,
            )
            await conn.commit()

        self._write_event_log({
            "event_id": event_id,
            "aggregate_id": event.get("aggregate_id", ""),
            "event_type": event.get("event_type", "unknown"),
            "data": event.get("data", {}),
            "timestamp": timestamp,
            "version": version,
        })

        asyncio.ensure_future(self._run_projections(event_id, row))

        return event_id

    async def _next_version(self, aggregate_id: str) -> int:
        """Calcula próximo version para o aggregate."""
        async with aiosqlite.connect(str(self.db_path)) as conn:
            cur = await conn.execute(
                "SELECT COALESCE(MAX(version), 0) FROM events WHERE aggregate_id = ?",
                (aggregate_id,),
            )
            row = await cur.fetchone()
            return (row[0] or 0) + 1

    def _write_event_log(self, entry: dict):
        """Escreve entrada no log JSONL."""
        try:
            with open(self._event_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            pass

    async def get_events(
        self,
        aggregate_id: str = None,
        event_type: str = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Retorna eventos com filtros opcionais."""
        await self._ensure_db()
        query = "SELECT id, aggregate_id, event_type, data, timestamp, version FROM events"
        params = []
        conditions = []

        if aggregate_id:
            conditions.append("aggregate_id = ?")
            params.append(aggregate_id)
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        async with aiosqlite.connect(str(self.db_path)) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(query, params)
            rows = await cur.fetchall()
            results = []
            for row in rows:
                d = dict(row)
                d["data"] = json.loads(d["data"])
                results.append(d)
            return results

    async def get_aggregate_events(self, aggregate_id: str) -> list[dict]:
        """Retorna todos os eventos de um aggregate em ordem."""
        return await self.get_events(aggregate_id=aggregate_id, limit=10000)

    async def count_events(self, event_type: str = None) -> int:
        """Conta eventos, opcionalmente por tipo."""
        await self._ensure_db()
        async with aiosqlite.connect(str(self.db_path)) as conn:
            if event_type:
                cur = await conn.execute(
                    "SELECT COUNT(*) FROM events WHERE event_type = ?", (event_type,)
                )
            else:
                cur = await conn.execute("SELECT COUNT(*) FROM events")
            row = await cur.fetchone()
            return row[0] or 0

    async def save_snapshot(self, aggregate_id: str, state: dict, version: int) -> None:
        """Salva snapshot do estado de um aggregate."""
        await self._ensure_db()
        async with aiosqlite.connect(str(self.db_path)) as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO snapshots (aggregate_id, state, version, timestamp) VALUES (?, ?, ?, ?)",
                (aggregate_id, json.dumps(state, ensure_ascii=False), version, time.time()),
            )
            await conn.commit()

    async def get_snapshot(self, aggregate_id: str) -> Optional[dict]:
        """Recupera último snapshot do aggregate."""
        await self._ensure_db()
        async with aiosqlite.connect(str(self.db_path)) as conn:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                "SELECT * FROM snapshots WHERE aggregate_id = ?", (aggregate_id,)
            )
            row = await cur.fetchone()
            if row:
                d = dict(row)
                d["state"] = json.loads(d["state"])
                return d
            return None

    async def _run_projections(self, event_id: str, event_row: tuple):
        """Executa projeções assíncronas para o evento."""
        event = {
            "event_id": event_row[0],
            "aggregate_id": event_row[1],
            "event_type": event_row[2],
            "data": json.loads(event_row[3]),
            "timestamp": event_row[4],
            "version": event_row[5],
        }

        tasks = []
        for proj_name in list(self._projections.keys()):
            tasks.append(self._apply_projection(proj_name, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _apply_projection(self, projection_name: str, event: dict):
        """Aplica evento a uma projeção específica."""
        try:
            if projection_name not in self._read_models:
                self._read_models[projection_name] = {"events": [], "state": {}}

            model = self._read_models[projection_name]
            model["events"].append(event["event_id"])

            etype = event["event_type"]
            state = model["state"]

            if etype == "aggregate_created":
                agg_id = event["aggregate_id"]
                state[agg_id] = state.get(agg_id, {}) | event["data"]
            elif etype == "aggregate_updated":
                agg_id = event["aggregate_id"]
                if agg_id in state:
                    state[agg_id] = state[agg_id] | event["data"]
                else:
                    state[agg_id] = event["data"]
            elif etype == "aggregate_deleted":
                state.pop(event["aggregate_id"], None)

            if "_metrics" not in state:
                state["_metrics"] = {"total_events": 0, "by_type": {}}
            state["_metrics"]["total_events"] = len(model["events"])
            by_type = state["_metrics"]["by_type"]
            by_type[etype] = by_type.get(etype, 0) + 1

        except Exception:
            pass

    def register_projection(self, name: str) -> None:
        """Registra uma projeção (read model)."""
        if name not in self._projections:
            self._projections[name] = asyncio.get_event_loop().create_task(
                self._projection_loop(name)
            )
            self._read_models[name] = {"events": [], "state": {}}

    async def _projection_loop(self, name: str):
        """Loop da projeção (mantém viva)."""
        while True:
            await asyncio.sleep(3600)

    def get_read_model(self, name: str) -> Optional[dict]:
        """Retorna estado atual de um read model."""
        model = self._read_models.get(name)
        if model:
            return model["state"]
        return None

    async def rebuild_projection(self, name: str) -> int:
        """Reconstrói projeção a partir do zero."""
        events = await self.get_events(limit=50000)
        model = {"events": [], "state": {}}
        for e in events:
            model["events"].append(e["id"])
            etype = e["event_type"]
            state = model["state"]
            agg_id = e["aggregate_id"]
            data = e["data"]
            if etype == "aggregate_created":
                state[agg_id] = state.get(agg_id, {}) | data
            elif etype == "aggregate_updated":
                if agg_id in state:
                    state[agg_id] = state[agg_id] | data
                else:
                    state[agg_id] = data
            elif etype == "aggregate_deleted":
                state.pop(agg_id, None)
        self._read_models[name] = model
        return len(events)

    async def get_stats(self) -> dict:
        """Estatísticas do store."""
        await self._ensure_db()
        async with aiosqlite.connect(str(self.db_path)) as conn:
            cur_total = await conn.execute("SELECT COUNT(*) FROM events")
            row_total = await cur_total.fetchone()
            total = row_total[0]
            cur_snap = await conn.execute("SELECT COUNT(*) FROM snapshots")
            row_snap = await cur_snap.fetchone()
            snap = row_snap[0]
            cur_types = await conn.execute(
                "SELECT event_type, COUNT(*) as cnt FROM events GROUP BY event_type ORDER BY cnt DESC"
            )
            rows_types = await cur_types.fetchall()

        return {
            "total_events": total,
            "total_snapshots": snap,
            "events_by_type": dict(rows_types),
            "active_projections": len(self._projections),
            "db_path": str(self.db_path),
            "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
        }

    def close(self):
        """Fecha conexões e limpa recursos."""
        for task in self._projections.values():
            task.cancel()