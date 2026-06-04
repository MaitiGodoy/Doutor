from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from kernel.provider_router import ProviderRouter

logger = logging.getLogger("antimatter.consensus")

@dataclass
class Vote:
    agent_role: str
    provider_name: str
    recommendation: str
    confidence: float
    rationale: str
    alternatives: List[str] = field(default_factory=list)

@dataclass
class ConsensusResult:
    question: str
    votes: List[Vote]
    accepted: bool
    final_recommendation: str
    confidence: float
    conflicts: List[str] = field(default_factory=list)
    escalated: bool = False
    majority: str = ""


def _parse_agent_output(raw: str, agent_role: str, provider_name: str) -> Vote:
    recommendation = "approve"
    confidence = 0.7
    rationale = raw.strip()[:500]
    alternatives = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            recommendation = parsed.get("recommendation") or parsed.get("decision") or parsed.get("vote") or recommendation
            confidence = float(parsed.get("confidence") or parsed.get("score") or confidence)
            rationale = parsed.get("rationale") or parsed.get("reason") or parsed.get("explanation") or rationale
            alternatives = parsed.get("alternatives") or parsed.get("options") or []
    except (json.JSONDecodeError, ValueError, TypeError):
        if "reject" in raw.lower() or "block" in raw.lower() or "veto" in raw.lower():
            recommendation = "reject"
        elif "approved" in raw.lower() or "accept" in raw.lower():
            recommendation = "approve"
        elif "abstain" in raw.lower():
            recommendation = "abstain"
    return Vote(
        agent_role=agent_role,
        provider_name=provider_name,
        recommendation=recommendation,
        confidence=confidence,
        rationale=rationale,
        alternatives=alternatives,
    )


class ConsensusEngine:
    def __init__(self, router: ProviderRouter):
        self.router = router
        self._vote_history: List[ConsensusResult] = []

    async def gather_votes(
        self,
        question: str,
        context: Dict[str, Any],
        agent_roles: List[str],
        min_votes: int = 3,
        temperature_override: Optional[float] = None,
    ) -> List[Vote]:
        if len(agent_roles) < 1:
            return []
        assignments = self.router.get_diverse_providers(agent_roles)
        if len(assignments) < min_votes:
            logger.warning(f"gather_votes: only {len(assignments)}/{min_votes} providers available for {agent_roles}")

        async def _call_agent(role: str) -> Optional[Vote]:
            assignment = assignments.get(role)
            if not assignment:
                logger.warning(f"gather_votes: no provider assignment for {role}")
                return None
            provider_name, model_id = assignment
            provider_config = next((p for p in self.router.providers if p.name == provider_name), None)
            if not provider_config:
                return None
            try:
                client = self.router._get_client(provider_config)
                system_prompt = self._build_system_prompt(role, question)
                user_prompt = json.dumps(context, indent=2, ensure_ascii=False)
                resp = await asyncio.wait_for(
                    client.chat.completions.create(
                        model=model_id,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=temperature_override or 0.3,
                        max_tokens=1024,
                    ),
                    timeout=45,
                )
                raw = resp.choices[0].message.content or ""
                vote = _parse_agent_output(raw, role, provider_name)
                self.router.mark_success(provider_config)
                return vote
            except Exception as e:
                logger.error(f"gather_votes: {role} on {provider_name} FAILED: {e}")
                self.router.mark_failure(provider_config)
                return None

        tasks = [_call_agent(role) for role in agent_roles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        votes: List[Vote] = []
        for r in results:
            if isinstance(r, Vote):
                votes.append(r)
        return votes

    def resolve_conflicts(self, votes: List[Vote], escalation_threshold: float = 0.3) -> ConsensusResult:
        if not votes:
            return ConsensusResult(
                question="",
                votes=[],
                accepted=False,
                final_recommendation="no_votes",
                confidence=0.0,
                conflicts=["no_votes_cast"],
                escalated=True,
            )
        recs = [v.recommendation for v in votes]
        approve_count = sum(1 for r in recs if r == "approve")
        reject_count = sum(1 for r in recs if r == "reject")
        abstain_count = sum(1 for r in recs if r == "abstain")
        total_weighted = approve_count + reject_count
        total_votes = len(votes)
        if total_weighted == 0:
            majority = "abstain"
            accepted = False
            final_rec = "abstain"
            conflicts = ["all_abstained"]
            escalated = True
        elif max(approve_count, reject_count) / total_weighted >= (1 - escalation_threshold):
            majority = "approve" if approve_count > reject_count else "reject"
            accepted = True
            final_rec = majority
            conflicts = []
            escalated = False
            minority = "reject" if majority == "approve" else "approve"
            minority_count = reject_count if majority == "approve" else approve_count
            if minority_count > 0:
                conflicts.append(f"{minority_count}_dissenting")
        else:
            majority = "approve" if approve_count > reject_count else "reject"
            accepted = False
            final_rec = majority
            conflicts = [f"split_{approve_count}_{reject_count}_{abstain_count}"]
            escalated = True

        confidence = max(v.confidence for v in votes) if votes else 0.0
        return ConsensusResult(
            question="",
            votes=votes,
            accepted=accepted,
            final_recommendation=final_rec,
            confidence=confidence,
            conflicts=conflicts,
            escalated=escalated,
            majority=majority,
        )

    async def decide(
        self,
        question: str,
        context: Dict[str, Any],
        agent_roles: List[str],
        min_votes: int = 3,
        escalation_threshold: float = 0.3,
    ) -> ConsensusResult:
        votes = await self.gather_votes(question, context, agent_roles, min_votes)
        result = self.resolve_conflicts(votes, escalation_threshold)
        result.question = question
        self._vote_history.append(result)
        logger.info(f"Consensus on '{question[:60]}...': {result.final_recommendation} (conflicts={result.conflicts}, escalated={result.escalated})")
        return result

    def _build_system_prompt(self, role: str, question: str) -> str:
        return f"""You are {role} in a multi-agent consensus system. Analyze the following question and context.

Your task: provide your independent recommendation with confidence level.

Output JSON with these exact keys:
- "recommendation": one of "approve", "reject", "abstain"
- "confidence": float 0.0-1.0
- "rationale": brief explanation (max 300 chars)
- "alternatives": list of alternative approaches if rejecting

Question: {question}

Remember: your vote should reflect your role's expertise. You do not need to agree with other agents."""
