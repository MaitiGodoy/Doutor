"""
Strategy & Intelligence Suite – multi-agent strategic analysis.
StrategyAgent: SWOT, market analysis, pivot suggestions.
IntelligenceAgent: synthesis, pattern detection, forecasting.
DarwinAgent: evolutionary optimization, fitness evaluation, mutation.
All integrate with memory_store to consume research data.
Zero stubs. 100% funcional e assíncrono.
"""
import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.provider_router import get_provider_router
from kernel.guards import SecurityGuard
from kernel.autonomy.core.agent_loop import AutonomousAgentLoop, AgentContext
from kernel.memory_store import MemoryStore


BASE_DIR = Path(__file__).resolve().parents[2]
LOG_PATH = BASE_DIR / "logs" / "strategy_intelligence.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class StrategyAgent(AutonomousAgentLoop):
    """Strategic analysis agent: SWOT, market positioning, pivot suggestions."""

    def __init__(self, goal: str = "strategic analysis", max_iterations: int = 3, dry_run: bool = True):
        super().__init__(goal=goal, max_iterations=max_iterations, dry_run=dry_run)
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.memory = MemoryStore()

    async def analyze_market(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Perform SWOT analysis using research data from memory_store."""
        # Fetch latest research events
        research_events = self.memory.get_events(event_type="agent_perceived", limit=20)
        research_data = [e.get("data", {}) for e in research_events]

        prompt = (
            "Perform a SWOT analysis (Strengths, Weaknesses, Opportunities, Threats) "
            "for the current market context based on this research data:\n"
            f"{json.dumps(research_data, ensure_ascii=False)[:4000]}"
        )

        guard_res = self.guard.validate_input(prompt, context={"chain_id": self.ctx.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard", "details": guard_res.model_dump() if hasattr(guard_res, "model_dump") else guard_res.__dict__}

        swot = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            swot_json = json.loads(swot)
        except json.JSONDecodeError:
            swot_json = {"raw": swot}

        result = {
            "analysis_type": "swot",
            "swot": swot_json,
            "data_points": len(research_data),
            "timestamp": time.time(),
        }
        self._log_strategy("analyze_market", result)
        return result

    async def optimize_loop(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest loop optimizations based on performance metrics."""
        prompt = (
            "Given these performance metrics, suggest 3 concrete optimizations for the autonomous agent loop:\n"
            f"{json.dumps(metrics, ensure_ascii=False)}"
        )
        optimization = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            opt_json = json.loads(optimization)
        except json.JSONDecodeError:
            opt_json = {"raw": optimization}

        result = {
            "analysis_type": "loop_optimization",
            "optimizations": opt_json,
            "based_on_metrics": metrics,
            "timestamp": time.time(),
        }
        self._log_strategy("optimize_loop", result)
        return result

    async def suggest_pivot(self, signals: List[str]) -> Dict[str, Any]:
        """Suggest strategic pivots based on market signals."""
        prompt = (
            "Based on these market signals, suggest 2-3 strategic pivots with rationale:\n"
            f"{json.dumps(signals, ensure_ascii=False)}"
        )
        pivot = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            pivot_json = json.loads(pivot)
        except json.JSONDecodeError:
            pivot_json = {"raw": pivot}

        result = {
            "analysis_type": "pivot_suggestion",
            "pivots": pivot_json,
            "trigger_signals": signals,
            "timestamp": time.time(),
        }
        self._log_strategy("suggest_pivot", result)
        return result

    def _log_strategy(self, action: str, payload: Dict[str, Any]) -> None:
        entry = {
            "timestamp": time.time(),
            "run_id": self.ctx.run_id,
            "chain_id": self.ctx.chain_id,
            "agent": "StrategyAgent",
            "action": action,
            "payload": payload,
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class IntelligenceAgent(AutonomousAgentLoop):
    """Intelligence synthesis agent: pattern detection, forecasting, synthesis."""

    def __init__(self, goal: str = "intelligence synthesis", max_iterations: int = 3, dry_run: bool = True):
        super().__init__(goal=goal, max_iterations=max_iterations, dry_run=dry_run)
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.memory = MemoryStore()

    async def synthesize_research(self, query: str) -> Dict[str, Any]:
        """Synthesize multiple research sources into coherent intelligence."""
        # Fetch research from memory
        research_events = self.memory.get_events(event_type="agent_acted", limit=30)
        research_data = [e.get("data", {}) for e in research_events]

        prompt = (
            f"Synthesize intelligence for query '{query}' from these research actions:\n"
            f"{json.dumps(research_data, ensure_ascii=False)[:4000]}"
        )

        guard_res = self.guard.validate_input(prompt, context={"chain_id": self.ctx.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard", "details": guard_res.model_dump() if hasattr(guard_res, "model_dump") else guard_res.__dict__}

        synthesis = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            syn_json = json.loads(synthesis)
        except json.JSONDecodeError:
            syn_json = {"raw": synthesis}

        result = {
            "analysis_type": "synthesis",
            "query": query,
            "synthesis": syn_json,
            "sources_count": len(research_data),
            "timestamp": time.time(),
        }
        self._log_intelligence("synthesize_research", result)
        return result

    async def detect_patterns(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Detect patterns in recent agent activity."""
        events = self.memory.get_events(limit=100)
        event_data = [{"type": e.get("event_type"), "data": e.get("data", {}), "ts": e.get("timestamp")} for e in events]

        prompt = (
            f"Detect patterns and anomalies in these events from the last {time_window_hours} hours:\n"
            f"{json.dumps(event_data, ensure_ascii=False)[:4000]}"
        )
        patterns = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            pat_json = json.loads(patterns)
        except json.JSONDecodeError:
            pat_json = {"raw": patterns}

        result = {
            "analysis_type": "pattern_detection",
            "patterns": pat_json,
            "events_analyzed": len(event_data),
            "timestamp": time.time(),
        }
        self._log_intelligence("detect_patterns", result)
        return result

    async def forecast(self, horizon_days: int = 7) -> Dict[str, Any]:
        """Generate short-term forecast based on current trends."""
        research_events = self.memory.get_events(event_type="agent_perceived", limit=20)
        research_data = [e.get("data", {}) for e in research_events]

        prompt = (
            f"Generate a {horizon_days}-day forecast based on current observations:\n"
            f"{json.dumps(research_data, ensure_ascii=False)[:3000]}"
        )
        forecast = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            fc_json = json.loads(forecast)
        except json.JSONDecodeError:
            fc_json = {"raw": forecast}

        result = {
            "analysis_type": "forecast",
            "horizon_days": horizon_days,
            "forecast": fc_json,
            "timestamp": time.time(),
        }
        self._log_intelligence("forecast", result)
        return result

    def _log_intelligence(self, action: str, payload: Dict[str, Any]) -> None:
        entry = {
            "timestamp": time.time(),
            "run_id": self.ctx.run_id,
            "chain_id": self.ctx.chain_id,
            "agent": "IntelligenceAgent",
            "action": action,
            "payload": payload,
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


class DarwinAgent(AutonomousAgentLoop):
    """Evolutionary optimization agent: fitness evaluation, mutation, selection."""

    def __init__(self, goal: str = "evolutionary optimization", max_iterations: int = 5, dry_run: bool = True):
        super().__init__(goal=goal, max_iterations=max_iterations, dry_run=dry_run)
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.memory = MemoryStore()
        self.population: List[Dict[str, Any]] = []
        self.generation = 0

    async def evaluate_fitness(self, candidate: Dict[str, Any]) -> float:
        """Evaluate fitness of a candidate strategy."""
        prompt = (
            "Evaluate the fitness (0.0-1.0) of this strategy candidate:\n"
            f"{json.dumps(candidate, ensure_ascii=False)}"
        )
        fitness_str = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            fitness = float(fitness_str.strip())
        except ValueError:
            fitness = 0.5
        return max(0.0, min(1.0, fitness))

    async def mutate(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a mutated variant of a candidate."""
        prompt = (
            "Generate a mutated variant of this strategy (small variation, keep structure):\n"
            f"{json.dumps(candidate, ensure_ascii=False)}"
        )
        mutated = await self.router.route(prompt, context={"chain_id": self.ctx.chain_id}, priority="high")
        try:
            mut_json = json.loads(mutated)
        except json.JSONDecodeError:
            mut_json = {"raw": mutated, "parent": candidate}
        return mut_json

    async def evolve(self, initial_population: List[Dict[str, Any]], generations: int = 3) -> Dict[str, Any]:
        """Run evolutionary optimization."""
        self.population = initial_population
        self.generation = 0

        for gen in range(generations):
            self.generation = gen + 1
            # Evaluate fitness
            fitness_scores = []
            for candidate in self.population:
                fitness = await self.evaluate_fitness(candidate)
                fitness_scores.append((candidate, fitness))

            # Sort by fitness
            fitness_scores.sort(key=lambda x: x[1], reverse=True)
            top_k = max(1, len(fitness_scores) // 2)
            survivors = [c for c, _ in fitness_scores[:top_k]]

            # Mutate survivors to create next generation
            new_population = survivors.copy()
            while len(new_population) < len(self.population):
                parent = survivors[len(new_population) % len(survivors)]
                child = await self.mutate(parent)
                new_population.append(child)

            self.population = new_population

        # Return best candidate
        best = fitness_scores[0] if fitness_scores else (self.population[0], 0.5) if self.population else ({}, 0.0)
        result = {
            "analysis_type": "evolution",
            "best_candidate": best[0],
            "best_fitness": best[1],
            "generations": generations,
            "final_population_size": len(self.population),
            "timestamp": time.time(),
        }
        self._log_darwin("evolve", result)
        return result

    def _log_darwin(self, action: str, payload: Dict[str, Any]) -> None:
        entry = {
            "timestamp": time.time(),
            "run_id": self.ctx.run_id,
            "chain_id": self.ctx.chain_id,
            "agent": "DarwinAgent",
            "action": action,
            "payload": payload,
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")