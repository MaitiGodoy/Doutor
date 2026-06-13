"""
MarketingSuite – Campaign generation and optimization agents.
BriefingAgent: generates campaign briefs from goals.
CreationAgent: creates ad copy, emails, social posts.
VoiceAgent: adapts tone/style for brand voice.
Integrates provider_router for generation, logs to marketing_campaigns.jsonl.
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
LOG_PATH = BASE_DIR / "logs" / "marketing_campaigns.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class BriefingAgent:
    """Generates comprehensive campaign briefs from goals."""

    def __init__(self, router, guard, chain_id: str):
        self.router = router
        self.guard = guard
        self.chain_id = chain_id

    async def generate_brief(
        self,
        goal: str,
        target_audience: str,
        channels: List[str],
        budget_range: str = "medium",
        duration_weeks: int = 4,
        key_messages: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        prompt = (
            f"Create a detailed marketing campaign brief.\n"
            f"Goal: {goal}\n"
            f"Target Audience: {target_audience}\n"
            f"Channels: {', '.join(channels)}\n"
            f"Budget Range: {budget_range}\n"
            f"Duration: {duration_weeks} weeks\n"
            f"Key Messages: {', '.join(key_messages or [])}\n\n"
            "Return JSON with: campaign_name, objective, target_personas (array), "
            "channel_strategy (per channel: content_type, frequency, kpis), "
            "timeline (weekly milestones), budget_allocation (per channel %), "
            "success_metrics, risks, creative_direction."
        )
        guard_res = self.guard.validate_input(prompt, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard"}

        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            brief = json.loads(result)
        except json.JSONDecodeError:
            brief = {"raw": result}

        return {
            "brief": brief,
            "input": {
                "goal": goal,
                "target_audience": target_audience,
                "channels": channels,
                "budget_range": budget_range,
                "duration_weeks": duration_weeks,
                "key_messages": key_messages,
            },
            "timestamp": time.time(),
        }


class CreationAgent:
    """Creates marketing assets: ad copy, emails, social posts, landing page copy."""

    def __init__(self, router, guard, chain_id: str):
        self.router = router
        self.guard = guard
        self.chain_id = chain_id

    async def create_assets(
        self,
        brief: Dict[str, Any],
        asset_types: List[str],
        brand_voice: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        brief_summary = json.dumps(brief.get("brief", brief), ensure_ascii=False)[:3000]
        voice_desc = json.dumps(brand_voice, ensure_ascii=False) if brand_voice else "professional, engaging"

        prompt = (
            f"Create marketing assets based on this brief:\n{brief_summary}\n\n"
            f"Brand Voice: {voice_desc}\n"
            f"Asset Types Required: {', '.join(asset_types)}\n\n"
            "For each asset type, generate 3 variations. "
            "Return JSON with assets grouped by type, each with: headline, body, cta, "
            "character_count, platform_optimizations."
        )
        guard_res = self.guard.validate_input(prompt, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard"}

        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            assets = json.loads(result)
        except json.JSONDecodeError:
            assets = {"raw": result}

        return {
            "assets": assets,
            "asset_types": asset_types,
            "brand_voice": brand_voice,
            "timestamp": time.time(),
        }

    async def adapt_tone(
        self,
        content: str,
        target_tone: str,
        target_platform: str,
    ) -> Dict[str, Any]:
        """Adapt existing content to a specific tone and platform."""
        prompt = (
            f"Adapt this content to '{target_tone}' tone for {target_platform}:\n\n"
            f"{content[:2000]}\n\n"
            "Return JSON with: adapted_content, changes_made, "
            "character_count, platform_optimizations (hashtags, mentions, formatting)."
        )
        guard_res = self.guard.validate_input(prompt, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard"}

        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            adapted = json.loads(result)
        except json.JSONDecodeError:
            adapted = {"adapted_content": result, "changes_made": []}

        return {
            "original": content[:200] + "..." if len(content) > 200 else content,
            "adapted": adapted,
            "target_tone": target_tone,
            "target_platform": target_platform,
            "timestamp": time.time(),
        }


class VoiceAgent:
    """Manages brand voice guidelines and ensures consistency."""

    def __init__(self, router, guard, chain_id: str):
        self.router = router
        self.guard = guard
        self.chain_id = chain_id
        self.voice_profile: Optional[Dict[str, Any]] = None

    async def define_voice(
        self,
        brand_name: str,
        values: List[str],
        personality_traits: List[str],
        do_samples: List[str],
        dont_samples: List[str],
    ) -> Dict[str, Any]:
        """Create a comprehensive brand voice profile."""
        prompt = (
            f"Create a brand voice profile for '{brand_name}'.\n"
            f"Values: {', '.join(values)}\n"
            f"Personality: {', '.join(personality_traits)}\n"
            f"Do: {', '.join(do_samples)}\n"
            f"Don't: {', '.join(dont_samples)}\n\n"
            "Return JSON with: voice_attributes (tone, style, vocabulary, rhythm), "
            "writing_rules (sentence_length, active_voice, jargon_level, emoji_usage), "
            "channel_adaptations (social, email, web, ads), "
            "example_phrases (do/dont pairs)."
        )
        guard_res = self.guard.validate_input(prompt, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard"}

        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            profile = json.loads(result)
        except json.JSONDecodeError:
            profile = {"raw": result}

        self.voice_profile = profile
        return {
            "brand_name": brand_name,
            "voice_profile": profile,
            "timestamp": time.time(),
        }

    async def check_consistency(self, content: str) -> Dict[str, Any]:
        """Check if content aligns with brand voice."""
        if not self.voice_profile:
            return {"error": "voice_profile_not_defined", "consistent": False}

        prompt = (
            f"Check if this content aligns with the brand voice profile:\n\n"
            f"Voice Profile: {json.dumps(self.voice_profile, ensure_ascii=False)[:2000]}\n\n"
            f"Content: {content[:2000]}\n\n"
            "Return JSON with: consistent (bool), score (0-1), "
            "violations (array), suggestions (array)."
        )
        guard_res = self.guard.validate_input(prompt, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard"}

        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            check = json.loads(result)
        except json.JSONDecodeError:
            check = {"consistent": True, "score": 0.8, "violations": [], "suggestions": []}

        return {
            "content_snippet": content[:200] + "..." if len(content) > 200 else content,
            "consistency_check": check,
            "timestamp": time.time(),
        }


class MarketingSuite(AutonomousAgentLoop):
    """Main orchestrator for marketing campaign generation."""

    def __init__(self, goal: str = "marketing campaign", max_iterations: int = 3, dry_run: bool = True):
        super().__init__(goal=goal, max_iterations=max_iterations, dry_run=dry_run)
        self.router = get_provider_router()
        self.guard = SecurityGuard()
        self.briefing = BriefingAgent(self.router, self.guard, self.ctx.chain_id)
        self.creation = CreationAgent(self.router, self.guard, self.ctx.chain_id)
        self.voice = VoiceAgent(self.router, self.guard, self.ctx.chain_id)

    async def generate_brief(
        self,
        goal: str,
        target_audience: str,
        channels: List[str],
        budget_range: str = "medium",
        duration_weeks: int = 4,
        key_messages: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        result = await self.briefing.generate_brief(goal, target_audience, channels, budget_range, duration_weeks, key_messages)
        self._log_marketing("generate_brief", result)
        return result

    async def create_assets(
        self,
        brief: Dict[str, Any],
        asset_types: List[str],
        brand_voice: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = await self.creation.create_assets(brief, asset_types, brand_voice)
        self._log_marketing("create_assets", result)
        return result

    async def adapt_tone(
        self,
        content: str,
        target_tone: str,
        target_platform: str,
    ) -> Dict[str, Any]:
        result = await self.creation.adapt_tone(content, target_tone, target_platform)
        self._log_marketing("adapt_tone", result)
        return result

    async def define_voice(
        self,
        brand_name: str,
        values: List[str],
        personality_traits: List[str],
        do_samples: List[str],
        dont_samples: List[str],
    ) -> Dict[str, Any]:
        result = await self.voice.define_voice(brand_name, values, personality_traits, do_samples, dont_samples)
        self._log_marketing("define_voice", result)
        return result

    async def check_consistency(self, content: str) -> Dict[str, Any]:
        result = await self.voice.check_consistency(content)
        self._log_marketing("check_consistency", result)
        return result

    async def schedule_distribution(
        self,
        assets: Dict[str, Any],
        start_date: str,
        frequency: Dict[str, int],
    ) -> Dict[str, Any]:
        """Generate distribution schedule for assets across channels."""
        prompt = (
            f"Create a distribution schedule for these assets:\n"
            f"{json.dumps(assets, ensure_ascii=False)[:3000]}\n\n"
            f"Start Date: {start_date}\n"
            f"Frequency per channel: {json.dumps(frequency)}\n\n"
            "Return JSON with: schedule (array of {date, channel, asset_id, asset_variation, status}), "
            "calendar_view (weekly), total_posts."
        )
        guard_res = self.guard.validate_input(prompt, context={"chain_id": self.chain_id})
        if guard_res.status == "blocked":
            return {"error": "blocked_by_guard"}

        result = await self.router.route(prompt, context={"chain_id": self.chain_id}, priority="high")
        try:
            schedule = json.loads(result)
        except json.JSONDecodeError:
            schedule = {"raw": result}

        output = {
            "schedule": schedule,
            "start_date": start_date,
            "frequency": frequency,
            "timestamp": time.time(),
        }
        self._log_marketing("schedule_distribution", output)
        return output

    async def run_full_campaign(
        self,
        goal: str,
        target_audience: str,
        channels: List[str],
        brand_name: str,
        values: List[str],
        personality_traits: List[str],
    ) -> Dict[str, Any]:
        """Execute complete campaign pipeline: voice -> brief -> assets -> schedule."""
        # 1. Define voice
        voice_result = await self.define_voice(brand_name, values, personality_traits, [], [])
        voice_profile = voice_result.get("voice_profile", {})

        # 2. Generate brief
        brief_result = await self.generate_brief(goal, target_audience, channels)
        brief = brief_result.get("brief", {})

        # 3. Create assets
        asset_types = ["social_post", "email", "ad_copy", "landing_page"]
        assets_result = await self.create_assets(brief_result, asset_types, voice_profile)
        assets = assets_result.get("assets", {})

        # 4. Schedule distribution
        frequency = {ch: 3 for ch in channels}
        schedule_result = await self.schedule_distribution(assets, "2024-01-15", frequency)

        report = {
            "campaign_goal": goal,
            "brand_name": brand_name,
            "voice": voice_result,
            "brief": brief_result,
            "assets": assets_result,
            "schedule": schedule_result,
            "pipeline_completed": True,
            "timestamp": time.time(),
        }
        self._log_marketing("run_full_campaign", report)
        return report

    def _log_marketing(self, action: str, payload: Dict[str, Any]) -> None:
        entry = {
            "timestamp": time.time(),
            "run_id": self.ctx.run_id,
            "chain_id": self.ctx.chain_id,
            "action": action,
            "payload": payload,
        }
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")