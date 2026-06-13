"""
GEOrchestrator – Geolocation optimization orchestrator.
Coordinates ScoutAgent, ContextBuilderAgent, ValidatorAgent for local SEO/GEO.
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


BASE_DIR = Path(__file__).resolve().parents[2]
LOG_PATH = BASE_DIR / "logs" / "geo_orchestrator.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class ScoutAgent:
    """Finds local entities (businesses, POIs, landmarks) for a location/category."""

    def __init__(self, router, guard, chain_id: str):
        self.router = router
        self.guard = guard
        self.chain_id = chain_id

    async def scout(self, location: str, category: str, radius_km: int = 5) -> Dict[str, Any]:
        prompt = (
            f"List 10 real local entities (businesses, POIs, landmarks) in {location} "
            f"for category '{category}' within {radius_km}km radius. "
            "Return JSON array with: name, address, lat, lng, category, rating, review_count, "
            "website, phone, hours, description."
        )
        guard_res = self.guard.validate_input(prompt, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard", "entities": []}

        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            entities = json.loads(result)
            if not isinstance(entities, list):
                entities = []
        except json.JSONDecodeError:
            entities = []

        return {
            "location": location,
            "category": category,
            "radius_km": radius_km,
            "entities": entities[:10],
            "count": len(entities),
            "timestamp": time.time(),
        }


class ContextBuilderAgent:
    """Builds cultural/regional context for a location."""

    def __init__(self, router, guard, chain_id: str):
        self.router = router
        self.guard = guard
        self.chain_id = chain_id

    async def build_context(self, location: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        entity_names = [e.get("name", "") for e in entities[:5]]
        prompt = (
            f"Build cultural and regional context for '{location}' considering these entities: "
            f"{', '.join(entity_names)}. "
            "Return JSON with: demographics, local_keywords, cultural_events, "
            "seasonal_patterns, language_variants, competitor_landscape, "
            "user_intent_signals, content_gaps."
        )
        guard_res = self.guard.validate_input(prompt, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard", "context": {}}

        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            context = json.loads(result)
        except json.JSONDecodeError:
            context = {}

        return {
            "location": location,
            "context": context,
            "entity_count": len(entities),
            "timestamp": time.time(),
        }


class ValidatorAgent:
    """Validates GEO data quality and compliance."""

    def __init__(self, router, guard, chain_id: str):
        self.router = router
        self.guard = guard
        self.chain_id = chain_id

    async def validate(self, location: str, entities: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            f"Validate GEO data quality for '{location}'. "
            f"Entities: {len(entities)} items. Context keys: {list(context.get('context', {}).keys())}. "
            "Check: NAP consistency, schema markup readiness, duplicate detection, "
            "category accuracy, review authenticity signals, "
            "compliance with Google Business Profile guidelines. "
            "Return JSON with: score (0-1), issues (array), warnings (array), recommendations (array)."
        )
        guard_res = self.guard.validate_input(prompt, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard", "validation": {}}

        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            validation = json.loads(result)
        except json.JSONDecodeError:
            validation = {"score": 0.5, "issues": [], "warnings": [], "recommendations": []}

        return {
            "location": location,
            "validation": validation,
            "timestamp": time.time(),
        }


class GEOrchestrator(AutonomousAgentLoop):
    """Orchestrates GEO optimization: scout -> context -> validate -> report."""

    def __init__(self, goal: str = "geo optimization", max_iterations: int = 3, dry_run: bool = True):
        super().__init__(goal=goal, max_iterations=max_iterations, dry_run=dry_run)
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.scout_agent = ScoutAgent(self.router, self.guard, self.ctx.chain_id)
        self.context_builder = ContextBuilderAgent(self.router, self.guard, self.ctx.chain_id)
        self.validator = ValidatorAgent(self.router, self.guard, self.ctx.chain_id)

    async def scout(self, location: str, category: str, radius_km: int = 5) -> Dict[str, Any]:
        """Find local entities for location/category."""
        result = await self.scout_agent.scout(location, category, radius_km)
        self._log_geo("scout", result)
        return result

    async def build_context(self, location: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build cultural/regional context."""
        result = await self.context_builder.build_context(location, entities)
        self._log_geo("build_context", result)
        return result

    async def validate(self, location: str, entities: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate GEO data quality."""
        result = await self.validator.validate(location, entities, context)
        self._log_geo("validate", result)
        return result

    async def run_full_pipeline(self, location: str, category: str, radius_km: int = 5) -> Dict[str, Any]:
        """Execute complete GEO pipeline: scout -> context -> validate."""
        # Step 1: Scout entities
        scout_result = await self.scout(location, category, radius_km)
        entities = scout_result.get("entities", [])

        # Step 2: Build context
        context_result = await self.build_context(location, entities)
        context = context_result.get("context", {})

        # Step 3: Validate
        validation_result = await self.validate(location, entities, context_result)

        # Final report
        report = {
            "location": location,
            "category": category,
            "radius_km": radius_km,
            "scout": scout_result,
            "context": context_result,
            "validation": validation_result,
            "pipeline_completed": True,
            "timestamp": time.time(),
        }
        self._log_geo("run_full_pipeline", report)
        return report

    def _log_geo(self, action: str, payload: Dict[str, Any]) -> None:
        entry = {
            "timestamp": time.time(),
            "run_id": self.ctx.run_id,
            "chain_id": self.ctx.chain_id,
            "action": action,
            "payload": payload,
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")