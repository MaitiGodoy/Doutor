import asyncio
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
import time

from .agents.scout_entity import GEO_EntityScout
from .agents.context_builder import GEO_ContextBuilder
from .agents.fact_council import GEO_FactCouncil
from .agents.format_planners import GEO_FormatPlanners
from .agents.entity_writer import GEO_EntityWriter
from .agents.hallucination_guard import GEO_HallucinationGuard
from .agents.visibility_tracker import GEO_VisibilityTracker
from .generators.knowledge_engine import GEO_KnowledgeEngine
from .agents.authority_builder import GEO_AuthorityBuilder
from .utils.cache_redis import RedisCache
from .utils.metrics import GEOMetrics

logger = logging.getLogger(__name__)

@dataclass
class GEOMission:
    brand: str
    target_keywords: List[str]
    competitors: List[str]
    target_urls: List[str]
    budget_daily_requests: int = 10000

class GEOResult:
    def __init__(self, **kwargs):
        self.brand_authority_score = kwargs.get("brand_authority_score", 0.0)
        self.visibility_index = kwargs.get("visibility_index", 0.0)
        self.competitor_gap = kwargs.get("competitor_gap", {})
        self.content_opportunities = kwargs.get("content_opportunities", [])
        self.citation_sources = kwargs.get("citation_sources", [])
        self.serp_positions = kwargs.get("serp_positions", {})
        self.recommendations_priority = kwargs.get("recommendations_priority", [])
        self.estimated_impact_score = kwargs.get("estimated_impact_score", 0.0)
        self.generated_content = kwargs.get("generated_content", "")
        self.schemas = kwargs.get("schemas", [])
        self.hallucination_risk = kwargs.get("hallucination_risk", 1.0)

class GuruGEOOrchestrator:
    def __init__(self, mission: GEOMission, redis_url: str = "redis://localhost:6379"):
        self.mission = mission
        self.cache = RedisCache(redis_url)
        self.scout = GEO_EntityScout(cache=self.cache)
        self.builder = GEO_ContextBuilder()
        self.council = GEO_FactCouncil()
        self.planners = GEO_FormatPlanners()
        self.writer = GEO_EntityWriter()
        self.guard = GEO_HallucinationGuard()
        self.tracker = GEO_VisibilityTracker()
        self.engine = GEO_KnowledgeEngine()
        self.authority = GEO_AuthorityBuilder()
        self.metrics = GEOMetrics()
    
    async def execute_mission(self) -> GEOResult:
        start = time.time()
        logger.info(f"🚀 Iniciando missão GEO para {self.mission.brand}")
        
        try:
            # FASE 1: Coleta de inteligência
            logger.info("📡 Fase 1: Coleta de entidades...")
            entities_data = await self.scout.extract({
                "brand": self.mission.brand,
                "urls": self.mission.target_urls
            })
            
            # FASE 2: Construção de contexto
            logger.info("🧠 Fase 2: Construindo contexto semântico...")
            context = await self.builder.build(entities_data, self.mission.target_keywords)
            
            # FASE 3: Validação factual (anti-hallucination)
            logger.info("🛡️ Fase 3: Validação factual...")
            if not await self.council.validate(context):
                raise ValueError("Council rejeitou contexto: risco de hallucination")
            
            # FASE 4: Planejamento de formatos A/B
            logger.info("📋 Fase 4: Planejamento de formatos...")
            plans = await self.planners.generate(context)
            
            # FASE 5: Geração de conteúdo entity-dense
            logger.info("✍️ Fase 5: Gerando conteúdo...")
            content = await self.writer.generate(plans["winner"])
            
            # FASE 6: Auditoria de qualidade
            logger.info("🔍 Fase 6: Auditoria de qualidade...")
            audit = await self.guard.audit(content)
            if not audit["passed"]:
                content = await self.writer.rewrite(content, audit["fixes"])
            
            # FASE 7: Injeção de schema e citações
            logger.info("🏷️ Fase 7: Injetando schema.org...")
            injection = await self.engine.inject(content, self.mission.brand)
            
            # FASE 8: Estratégia de autoridade
            logger.info("🏆 Fase 8: Construindo estratégia de autoridade...")
            authority_strategy = await self.authority.build_strategy(
                self.mission.brand, 
                entities_data.get("entities", [])
            )
            
            # FASE 9: Medição de visibilidade
            logger.info("📈 Fase 9: Medindo visibilidade...")
            visibility = await self.tracker.measure(self.mission.brand, content)
            
            # FASE 10: Cálculo de métricas
            authority_score = self.metrics.calculate_authority_score(
                {"cooccurrence_score": context["cooccurrence_score"], "citation_estimate": len(injection["citations"])},
                {},
                {k: v.get("rank", 5) for k, v in visibility["platforms"].items()}
            )
            
            elapsed = time.time() - start
            logger.info(f"✅ Missão completada em {elapsed:.1f}s | Authority: {authority_score:.1f}/100")
            
            return GEOResult(
                brand_authority_score=round(authority_score, 2),
                visibility_index=visibility["visibility_score"],
                competitor_gap={},
                content_opportunities=[f"Formato {plans['winner']}: {plans['plans'][plans['winner']]['format']}"],
                citation_sources=injection["citations"],
                serp_positions={k: v.get("rank", 5) for k, v in visibility["platforms"].items()},
                recommendations_priority=visibility["recommendations"],
                estimated_impact_score=self.metrics.estimate_impact([], authority_score),
                generated_content=content,
                schemas=injection["schemas"],
                hallucination_risk=audit["risk_score"]
            )
        
        except Exception as e:
            logger.error(f"❌ Missão falhou: {e}", exc_info=True)
            raise

# Factory
_orchestrator_instance = None

def get_geo_orchestrator(
    brand: str, 
    keywords: List[str], 
    competitors: List[str],
    urls: List[str]
) -> GuruGEOOrchestrator:
    global _orchestrator_instance
    if _orchestrator_instance is None:
        mission = GEOMission(
            brand=brand,
            target_keywords=keywords,
            competitors=competitors,
            target_urls=urls
        )
        _orchestrator_instance = GuruGEOOrchestrator(mission)
    return _orchestrator_instance