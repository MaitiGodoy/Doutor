import os, requests, json, time
from datetime import datetime
from kernel.utils import hash_payload, load_cache, save_cache

# APIs Free Tier
SERPER_API_KEY = os.getenv("SERPER_API_KEY")  # https://serper.dev (2500 free/mês)
NEWS_API_KEY = os.getenv("NEWS_API_KEY")      # https://newsapi.org (100 free/dia)

class ResearchAgent:
    def __init__(self, niche: str, audience: str, competitors: list = []):
        self.niche = niche
        self.audience = audience
        self.competitors = competitors
        self.cache = load_cache()
    
    def search_google_trends(self, query: str, geo: str = "BR") -> dict:
        """Busca volume e crescimento de keywords via Serper"""
        cache_key = f"trends_{query}_{geo}"
        if cache_key in self.cache and time.time() - self.cache[cache_key]["ts"] < 3600:
            return self.cache[cache_key]["data"]
        
        try:
            url = "https://google.serper.dev/search"
            headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
            payload = {"q": f"{query} trends {datetime.now().year}", "num": 10}
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            data = res.json()
            
            # Extrai insights
            trends = {
                "query": query,
                "results_count": len(data.get("organic", [])),
                "top_results": [{"title": r["title"], "snippet": r["snippet"], "url": r["link"]} 
                               for r in data.get("organic", [])[:5]],
                "related_searches": data.get("relatedSearches", [])[:10]
            }
            
            self.cache[cache_key] = {"data": trends, "ts": time.time()}
            save_cache(self.cache)
            return trends
        except Exception as e:
            print(f"[Research] Google Trends error: {e}")
            return {"query": query, "error": str(e)}
    
    def scan_reddit(self, subreddits: list = None) -> list:
        """Varre Reddit por discussões quentes do nicho"""
        if not subreddits:
            subreddits = ["marketing", "entrepreneur", "SaaS", "productivity", "sidehustle"]
        
        trending = []
        for sub in subreddits:
            try:
                url = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
                headers = {"User-Agent": "Omnisquad/1.0"}
                res = requests.get(url, headers=headers, timeout=30)
                data = res.json()
                
                for post in data["data"]["children"][:10]:
                    d = post["data"]
                    if d["score"] > 100 and d["num_comments"] > 20:
                        trending.append({
                            "source": f"reddit/r/{sub}",
                            "title": d["title"],
                            "score": d["score"],
                            "comments": d["num_comments"],
                            "url": f"https://reddit.com{d['permalink']}",
                            "created_utc": d["created_utc"],
                            "engagement_rate": d["num_comments"] / max(d["score"], 1)
                        })
                time.sleep(1)  # Rate limit
            except Exception as e:
                print(f"[Research] Reddit r/{sub} error: {e}")
        
        return sorted(trending, key=lambda x: x["engagement_rate"], reverse=True)[:20]
    
    def monitor_product_hunt(self) -> list:
        """Monitora lançamentos virais no Product Hunt"""
        try:
            res = requests.get("https://www.producthunt.com", timeout=30)
            return [{"source": "product_hunt", "note": "Implementar parser completo"}]
        except Exception as e:
            print(f"[Research] Product Hunt error: {e}")
            return []
    
    def news_jacking_scan(self) -> list:
        """Identifica notícias quentes para newsjacking"""
        if not NEWS_API_KEY:
            return [{"source": "newsapi", "note": "NEWS_API_KEY não configurada no .env"}]
        try:
            url = "https://newsapi.org/v2/top-headlines"
            params = {
                "country": "br",
                "category": "technology,business",
                "apiKey": NEWS_API_KEY,
                "pageSize": 20
            }
            res = requests.get(url, params=params, timeout=30)
            data = res.json()
            
            opportunities = []
            for article in data.get("articles", [])[:10]:
                opportunities.append({
                    "title": article["title"],
                    "source": article["source"]["name"],
                    "published_at": article["publishedAt"],
                    "url": article["url"],
                    "relevance_score": self._calculate_relevance(article["title"]),
                    "angle_suggestion": f"Conectar {article['title']} com {self.niche}"
                })
            
            return sorted(opportunities, key=lambda x: x["relevance_score"], reverse=True)[:5]
        except Exception as e:
            print(f"[Research] NewsAPI error: {e}")
            return []
    
    def competitor_watch(self) -> list:
        """Monitora movimentos da concorrência"""
        moves = []
        for competitor in self.competitors:
            try:
                url = "https://google.serper.dev/search"
                headers = {"X-API-KEY": SERPER_API_KEY}
                payload = {"q": f"{competitor} launch OR update OR new", "num": 5}
                res = requests.post(url, headers=headers, json=payload, timeout=30)
                data = res.json()
                
                for result in data.get("organic", [])[:3]:
                    moves.append({
                        "competitor": competitor,
                        "title": result["title"],
                        "snippet": result["snippet"],
                        "url": result["link"],
                        "detected_at": datetime.now().isoformat()
                    })
            except Exception as e:
                print(f"[Research] Competitor {competitor} error: {e}")
        
        return moves
    
    def _calculate_relevance(self, text: str) -> float:
        """Calcula relevância da notícia para o nicho (simplificado)"""
        keywords = self.niche.lower().split()
        text = text.lower()
        score = sum(1 for k in keywords if k in text)
        return score / len(keywords)
    
    def generate_intelligence_briefing(self) -> dict:
        """Gera briefing completo de inteligência de mercado"""
        print("[Research] Iniciando varredura completa...")
        
        trends = self.search_google_trends(f"{self.niche} {self.audience}")
        reddit_hot = self.scan_reddit()
        newsjacking = self.news_jacking_scan()
        competitors = self.competitor_watch()
        
        emerging_keywords = trends.get("related_searches", [])[:10]
        viral_angles = [r["title"] for r in reddit_hot[:5] if r["engagement_rate"] > 0.1]
        
        briefing = {
            "generated_at": datetime.now().isoformat(),
            "niche": self.niche,
            "audience": self.audience,
            "trending_topics": list(set([t.split()[0] for t in emerging_keywords if t.split()])),
            "emerging_keywords": [{"keyword": k, "source": "google_trends"} for k in emerging_keywords],
            "viral_angles": viral_angles,
            "reddit_discussions": reddit_hot[:10],
            "newsjacking_opportunities": newsjacking,
            "competitor_moves": competitors,
            "recommended_actions": self._generate_recommendations(trends, reddit_hot, newsjacking)
        }
        
        self.cache[f"briefing_{self.niche}"] = {"data": briefing, "ts": time.time()}
        save_cache(self.cache)
        
        return briefing
    
    def _generate_recommendations(self, trends: dict, reddit: list, news: list) -> list:
        """Gera recomendações acionáveis baseadas nos dados"""
        recs = []
        if trends.get("related_searches"):
            recs.append(f" Criar conteúdo sobre: {', '.join(trends['related_searches'][:3])}")
        if reddit:
            top_topic = reddit[0]["title"]
            recs.append(f"💬 Participar da discussão no Reddit: {top_topic}")
        if news:
            recs.append(f"📰 Aproveitar newsjacking: {news[0]['title']}")
        return recs

async def inject_research_before_planning(input_data: dict) -> dict:
    """Chama research agent ANTES dos planejadores começarem"""
    niche = input_data.get("niche", "general")
    audience = input_data.get("audience", "general")
    competitors = input_data.get("competitors", [])
    
    researcher = ResearchAgent(niche, audience, competitors)
    briefing = researcher.generate_intelligence_briefing()
    
    input_data["market_intelligence"] = briefing
    input_data["research_timestamp"] = briefing["generated_at"]
    return input_data
