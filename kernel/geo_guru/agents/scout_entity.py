import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import logging
from ..utils.cache_redis import RedisCache
import re

logger = logging.getLogger(__name__)

class GEO_EntityScout:
    def __init__(self, cache: RedisCache = None):
        self.cache = cache
        self.session = None
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        ]
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def extract(self, mission: Dict) -> Dict:
        """Extrai entidades, citações e contexto da marca"""
        brand = mission["brand"]
        urls = mission.get("urls", [])
        
        tasks = [self._fetch_and_parse(url, brand) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        entities = []
        citations = []
        schemas = []
        
        for result in results:
            if isinstance(result, dict):
                entities.extend(result.get("entities", []))
                citations.extend(result.get("citations", []))
                schemas.extend(result.get("schemas", []))
        
        return {
            "brand": brand,
            "entities": list(set(entities))[:100],
            "citations": citations[:50],
            "schemas": schemas,
            "total_urls_analyzed": len(urls)
        }
    
    async def _fetch_and_parse(self, url: str, brand: str) -> Dict:
        cache_key = f"scout:{url}"
        if self.cache:
            cached = await self.cache.get(cache_key)
            if cached:
                return cached
        
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            async with self.session.get(url, headers=headers, timeout=30) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    data = await self._parse_entities(html, url, brand)
                    
                    if self.cache:
                        await self.cache.set(cache_key, data, ttl=7200)
                    
                    return data
        except Exception as e:
            logger.error(f"Scout fetch error for {url}: {e}")
        
        return {"entities": [], "citations": [], "schemas": []}
    
    async def _parse_entities(self, html: str, url: str, brand: str) -> Dict:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove scripts
        for tag in soup(["script", "style"]):
            tag.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        
        # Extrai entidades (pessoas, orgs, locais)
        entities = self._extract_entities_from_text(text, brand)
        
        # Extrai citações/menções
        citations = self._find_citations(text, brand)
        
        # Extrai schema.org
        schemas = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                import json
                schemas.append(json.loads(script.string))
            except:
                pass
        
        return {
            "entities": entities,
            "citations": citations,
            "schemas": schemas,
            "url": url
        }
    
    def _extract_entities_from_text(self, text: str, brand: str) -> List[str]:
        # Padrões básicos de entidades
        patterns = [
            r'\b[A-Z][a-z]+ (?:Ltda|SA|Inc|LLC)\b',
            r'\b(?:Dr|Prof|Eng)\.?\s+[A-Z][a-z]+ [A-Z][a-z]+\b',
            r'\b[A-Z]{2,}\b',
            r'\b(?:Brasil|São Paulo|Rio|EUA|Europa)\b'
        ]
        
        entities = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            entities.update(matches)
        
        # Adiciona brand e keywords relacionadas
        entities.add(brand)
        
        return list(entities)[:100]
    
    def _find_citations(self, text: str, brand: str) -> List[Dict]:
        # Busca menções da marca próximas a palavras de autoridade
        authority_words = ["fundador", "criador", "desenvolvido por", "método", "protocolo", "pesquisa"]
        citations = []
        
        for word in authority_words:
            pattern = rf'({brand}.*?{word}.{{50}}|{word}.*?{brand}.{{50}})'
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches[:5]:
                citations.append({
                    "text": match.strip()[:200],
                    "context": word
                })
        
        return citations[:20]