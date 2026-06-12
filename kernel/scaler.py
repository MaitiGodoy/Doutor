import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class ResourceRequest:
    task_id: str
    gpu_memory_mb: int
    compute_units: int
    priority: int  # 1-10 (10 = crÃ­tico)
    deadline: Optional[float] = None
    created_at: float = field(default_factory=time.time)

@dataclass
class AllocationResult:
    status: str
    gpu_id: int
    memory_allocated_mb: int
    compute_units_allocated: int
    estimated_wait_time: float = 0.0
    details: str = ""

class CuOptResourceScaler:
    def __init__(self):
        self.total_gpu_memory_mb = 0
        self.total_compute_units = 0
        self.available_memory = 0
        self.available_compute = 0
        self.active_tasks: Dict[str, ResourceRequest] = {}
        self.queue: List[ResourceRequest] = []
        self.history: List[Dict] = []
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        if self._initialized: return
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            self.total_gpu_memory_mb = info.total // (1024*1024)
            self.available_memory = self.total_gpu_memory_mb
            self.total_compute_units = pynvml.nvmlDeviceGetNumGpuCores(handle)
            self.available_compute = self.total_compute_units
            logger.info(f" GPU Detectada: {self.total_gpu_memory_mb}MB VRAM | {self.total_compute_units} Cores")
        except Exception as e:
            logger.warning(f"âš ï¸ DetecÃ§Ã£o GPU falhou ({e}). Usando fallback 16GB/100 cores.")
            self.total_gpu_memory_mb = 16384
            self.available_memory = 16384
            self.total_compute_units = 100
            self.available_compute = 100
        self._initialized = True

    async def request(self, req: ResourceRequest) -> AllocationResult:
        await self.initialize()
        async with self._lock:
            # AlocaÃ§Ã£o imediata se houver recursos
            if req.gpu_memory_mb <= self.available_memory and req.compute_units <= self.available_compute:
                return await self._allocate(req)
            
            # OtimizaÃ§Ã£o de fila (cuOpt logic)
            self.queue.append(req)
            self.queue.sort(key=lambda x: (-x.priority, x.deadline or 9999999999))
            
            wait_time = await self._optimize_queue()
            return AllocationResult(
                status="queued", gpu_id=-1, memory_allocated_mb=0,
                compute_units_allocated=0, estimated_wait_time=wait_time,
                details=f"PosiÃ§Ã£o {self.queue.index(req)+1} na fila otimizada"
            )

    async def release(self, task_id: str):
        async with self._lock:
            if task_id in self.active_tasks:
                req = self.active_tasks.pop(task_id)
                self.available_memory += req.gpu_memory_mb
                self.available_compute += req.compute_units
                self.history.append({"task_id": task_id, "action": "released", "ts": time.time()})
                logger.info(f" Liberado {task_id}. VRAM livre: {self.available_memory}MB")
                await self._process_queue()

    async def _allocate(self, req: ResourceRequest) -> AllocationResult:
        self.available_memory -= req.gpu_memory_mb
        self.available_compute -= req.compute_units
        self.active_tasks[req.task_id] = req
        self.history.append({"task_id": req.task_id, "action": "allocated", "ts": time.time()})
        return AllocationResult(
            status="allocated", gpu_id=0,
            memory_allocated_mb=req.gpu_memory_mb,
            compute_units_allocated=req.compute_units,
            details="AlocaÃ§Ã£o direta via cuOpt"
        )

    async def _optimize_queue(self) -> float:
        if not self.queue: return 0.0
        # HeurÃ­stica cuOpt: load_factor + bin_packing estimado
        load = 1.0 - (self.available_memory / max(self.total_gpu_memory_mb, 1))
        avg_mem = sum(r.gpu_memory_mb for r in self.active_tasks.values()) / max(len(self.active_tasks), 1)
        wait = (load * 25) + (self.queue[0].gpu_memory_mb / max(avg_mem, 1)) * 10
        return max(5.0, min(wait, 300.0))

    async def _process_queue(self):
        to_promote = []
        for req in self.queue[:]:
            if req.gpu_memory_mb <= self.available_memory and req.compute_units <= self.available_compute:
                to_promote.append(req)
                self.queue.remove(req)
        for req in to_promote:
            await self._allocate(req)

    def metrics(self) -> Dict[str, Any]:
        return {
            "gpu_vram_mb": {
                "total": self.total_gpu_memory_mb,
                "used": self.total_gpu_memory_mb - self.available_memory,
                "free": self.available_memory,
                "utilization_pct": round(((self.total_gpu_memory_mb - self.available_memory) / max(self.total_gpu_memory_mb, 1)) * 100, 1)
            },
            "compute_units": {
                "total": self.total_compute_units,
                "free": self.available_compute
            },
            "active_tasks": len(self.active_tasks),
            "queued_tasks": len(self.queue),
            "queue": [{"id": r.task_id, "priority": r.priority, "mem_mb": r.gpu_memory_mb} for r in self.queue]
        }

_scaler = None
async def get_scaler() -> CuOptResourceScaler:
    global _scaler
    if _scaler is None:
        _scaler = CuOptResourceScaler()
        await _scaler.initialize()
    return _scaler