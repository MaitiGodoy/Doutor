"""
Growth Agent — Doutor v5.0
Análise de mercado, tracking de competidores, sugestões de crescimento,
oportunidades de expansão e inteligência competitiva.
Hermes Agent participa como co-analista em todas as análises.
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from kernel.llm_client import call_llm

logger = logging.getLogger("doutor.growth")

# Import opcional do Hermes Bridge
try:
    from kernel.hermes_bridge import HermesBridge
    _hermes_growth = HermesBridge()
except Exception:
    _hermes_growth = None

GROWTH_SYSTEM_PROMPT = """You are a senior growth strategist and market analyst. 
Analyze the given market/niche and provide actionable growth insights.
Return valid JSON with: market_overview (string), growth_opportunities (array of {opportunity, impact, effort, timeline}),
competitor_landscape (string), recommended_strategies (array of {strategy, expected_roi, implementation_steps}),
key_metrics_to_track (array of strings), and risk_factors (array of strings)."""

COMPETITOR_SYSTEM_PROMPT = """You are a competitive intelligence analyst.
Analyze the given competitor and market position. Return valid JSON with:
competitor_overview (string), strengths (array), weaknesses (array), market_position (string),
threat_level (low/medium/high), recommended_counter_strategies (array of strings),
and gaps_to_exploit (array of strings)."""


class GrowthAgent:
    """Agente de crescimento e inteligência de mercado"""

    def __init__(self):
        self.last_analysis = {}

    async def market_analysis(self, niche: str, audience: str = "", region: str = "BR") -> Dict:
        """Analisa mercado e identifica oportunidades de crescimento (com Hermes)"""
        user_prompt = f"""
Niche: {niche}
Target Audience: {audience or "General"}
Region: {region}
Date: {datetime.now().strftime("%Y-%m-%d")}

Provide a comprehensive market analysis with growth opportunities.
Focus on digital marketing, SaaS, and online business trends.
"""
        try:
            # Análise principal pelo Doutor
            result = await call_llm("the_polymath", GROWTH_SYSTEM_PROMPT, user_prompt)
            result["niche"] = niche
            result["audience"] = audience
            result["region"] = region
            result["analyzed_at"] = datetime.now().isoformat()
            self.last_analysis = result

            # Hermes contribui com análise complementar (background)
            if _hermes_growth:
                try:
                    hermes_analysis = await _hermes_growth.participate_growth_analysis(
                        {"niche": niche, "audience": audience, "region": region},
                        "market"
                    )
                    result["hermes_insights"] = hermes_analysis.get("response", {})
                    logger.info(f"Hermes contribuiu na análise de mercado: {niche}")
                except Exception:
                    pass

            logger.info(f"Market analysis completed for niche: {niche}")
            return {"status": "ok", "data": result}
        except Exception as e:
            logger.error(f"Market analysis failed: {e}")
            return {"status": "error", "error": str(e), "niche": niche}

    async def competitor_tracking(self, competitors: List[str], niche: str = "") -> Dict:
        """Analisa competidores e sugere contra-estratégias"""
        if not competitors:
            return {"status": "error", "error": "No competitors provided"}

        results = []
        for comp in competitors:
            try:
                user_prompt = f"""
Competitor: {comp}
Niche: {niche or "Digital Marketing"}
Region: BR

Analyze this competitor's market position, strengths, weaknesses, and recommend counter-strategies.
"""
                result = await call_llm("the_scout", COMPETITOR_SYSTEM_PROMPT, user_prompt)
                result["competitor"] = comp
                result["analyzed_at"] = datetime.now().isoformat()
                results.append(result)
                logger.info(f"Competitor analyzed: {comp}")
            except Exception as e:
                logger.error(f"Competitor analysis failed for {comp}: {e}")
                results.append({"competitor": comp, "status": "error", "error": str(e)})

        # Gera análise consolidada
        consolidated = {
            "competitors_analyzed": len(results),
            "competitors": results,
            "threat_summary": self._summarize_threats(results),
            "analyzed_at": datetime.now().isoformat()
        }
        return {"status": "ok", "data": consolidated}

    async def growth_suggestions(self, business_type: str, current_metrics: Dict = None) -> Dict:
        """Gera sugestões de crescimento baseadas no tipo de negócio"""
        if current_metrics is None:
            current_metrics = {}

        metrics_str = json.dumps(current_metrics, indent=2) if current_metrics else "No metrics provided"
        user_prompt = f"""
Business Type: {business_type}
Current Metrics: {metrics_str}
Date: {datetime.now().strftime("%Y-%m-%d")}

Suggest 5-10 growth strategies for this business. For each strategy, provide:
- Strategy name
- Expected impact (high/medium/low)
- Effort required (high/medium/low)
- Timeline (weeks)
- Key implementation steps
- Success metrics
"""
        try:
            result = await call_llm("the_architect", GROWTH_SYSTEM_PROMPT, user_prompt)
            result["business_type"] = business_type
            result["generated_at"] = datetime.now().isoformat()
            logger.info(f"Growth suggestions generated for: {business_type}")
            return {"status": "ok", "data": result}
        except Exception as e:
            logger.error(f"Growth suggestions failed: {e}")
            return {"status": "error", "error": str(e), "business_type": business_type}

    def _summarize_threats(self, competitor_results: List[Dict]) -> Dict:
        """Sumariza nível de ameaça dos competidores"""
        levels = {"high": 0, "medium": 0, "low": 0, "unknown": 0}
        for r in competitor_results:
            threat = r.get("threat_level", "unknown")
            if threat in levels:
                levels[threat] += 1
            else:
                levels["unknown"] += 1
        return {
            "threat_distribution": levels,
            "total_competitors": len(competitor_results)
        }
