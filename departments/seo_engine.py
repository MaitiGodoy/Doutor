import os
import re
import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup, Comment


class SEOEngine:
    def __init__(self, output_dir: str = "output/html"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def optimize_site_seo_and_virality(self, directory: str = None) -> Dict:
        target = Path(directory) if directory else self.output_dir
        results = []
        for html_file in target.rglob("*.html"):
            result = self.optimize_file(str(html_file))
            results.append(result)
        return {
            "mode": "site_seo_optimization",
            "target": str(target),
            "files_processed": len(results),
            "results": results,
            "status": "success",
        }

    def optimize_site_keywords_and_meta(self, file_path: str, keywords: List[str], description: str = "") -> Dict:
        soup = self._load_soup(file_path)
        if not soup:
            return {"status": "error", "error": f"File not found: {file_path}"}

        title_tag = soup.find("title")
        if not title_tag:
            title_tag = soup.new_tag("title")
            if soup.head:
                soup.head.insert(0, title_tag)
            elif soup.html:
                head = soup.new_tag("head")
                soup.html.insert(0, head)
                head.insert(0, title_tag)

        kw_str = ", ".join(keywords[:10]) if keywords else ""
        meta_kw = soup.find("meta", attrs={"name": "keywords"})
        if meta_kw:
            meta_kw["content"] = kw_str
        else:
            if soup.head:
                new_meta = soup.new_tag("meta", attrs={"name": "keywords", "content": kw_str})
                soup.head.append(new_meta)

        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            meta_desc["content"] = description or kw_str[:160]
        else:
            if soup.head:
                new_desc = soup.new_tag("meta", attrs={"name": "description", "content": description or kw_str[:160]})
                soup.head.append(new_desc)

        self._inject_og_tags(soup, title_tag.string or "", description or kw_str[:160], keywords)
        self._inject_schema_jsonld(soup, title_tag.string or "", description or kw_str[:160])

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(str(soup))

        density = self.check_seo_keywords(str(soup), keywords)
        return {
            "status": "success",
            "file": file_path,
            "keywords_injected": len(keywords),
            "meta_updated": True,
            "og_tags_injected": True,
            "schema_injected": True,
            "keyword_density": density,
        }

    def check_seo_keywords(self, text: str, keywords: List[str]) -> Dict:
        text_lower = text.lower()
        total_words = len(re.findall(r'\b\w+\b', text_lower))
        results = {}
        for kw in keywords:
            kw_lower = kw.lower()
            count = len(re.findall(re.escape(kw_lower), text_lower))
            density = round(count / max(total_words, 1) * 100, 2)
            results[kw] = {"count": count, "density_pct": density}
        avg_density = sum(r["density_pct"] for r in results.values()) / max(len(results), 1)
        return {
            "keywords": results,
            "average_density_pct": round(avg_density, 2),
            "total_words": total_words,
            "recommendation": "optimal" if 1.0 <= avg_density <= 3.0 else ("low" if avg_density < 1.0 else "high"),
        }

    def run_vivar_seo_agent_loop(self, title: str, content: str, target_keyword: str) -> Dict:
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text()

        density = text.lower().count(target_keyword.lower()) / max(len(text.split()), 1) * 100

        keywords_in_title = 1 if target_keyword.lower() in title.lower() else 0
        h1_tags = soup.find_all("h1")
        keywords_in_h1 = sum(1 for h in h1_tags if target_keyword.lower() in h.get_text().lower())

        img_alts = soup.find_all("img")
        keywords_in_alts = sum(1 for img in img_alts if img.get("alt") and target_keyword.lower() in img.get("alt").lower())

        links = soup.find_all("a")
        internal_links = sum(1 for a in links if a.get("href", "").startswith("/") or not a.get("href", "").startswith("http"))
        external_links = len(links) - internal_links

        score = 0
        score += 25 if keywords_in_title > 0 else 0
        score += 15 if keywords_in_h1 > 0 else 0
        score += min(density * 8, 20)
        score += min(keywords_in_alts * 5, 10)
        score += min(internal_links, 15)
        score += min(external_links, 5)
        score += 10 if len(title) >= 30 and len(title) <= 60 else 0

        return {
            "title": title,
            "target_keyword": target_keyword,
            "metrics": {
                "keyword_density_pct": round(density, 2),
                "keywords_in_title": keywords_in_title,
                "keywords_in_h1": keywords_in_h1,
                "keywords_in_img_alts": keywords_in_alts,
                "internal_links": internal_links,
                "external_links": external_links,
                "title_length": len(title),
            },
            "seo_score": min(score, 100),
            "recommendations": self._generate_seo_recommendations(
                keywords_in_title, keywords_in_h1, density, keywords_in_alts, links, title
            ),
        }

    def optimize_file(self, file_path: str, config: Dict = None) -> Dict:
        soup = self._load_soup(file_path)
        if not soup:
            return {"status": "error", "error": f"File not found: {file_path}"}

        title_tag = soup.find("title")
        title = title_tag.string if title_tag else ""

        text = soup.get_text()
        word_count = len(re.findall(r'\b\w+\b', text))

        images = soup.find_all("img")
        missing_alt = sum(1 for img in images if not img.get("alt"))

        links = soup.find_all("a")
        broken_links = sum(1 for a in links if not a.get("href") or a.get("href") == "#" or a.get("href") == "")

        headings = {}
        for level in range(1, 7):
            headings[f"h{level}"] = len(soup.find_all(f"h{level}"))

        self._inject_og_tags(soup, title, "", [])
        self._inject_schema_jsonld(soup, title, "")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(str(soup))

        return {
            "status": "success",
            "file": file_path,
            "seo_score": self._calculate_score(word_count, images, missing_alt, broken_links, headings, title),
            "metrics": {
                "word_count": word_count,
                "images": len(images),
                "images_missing_alt": missing_alt,
                "links": len(links),
                "broken_links": broken_links,
                "headings": headings,
                "has_title": bool(title),
                "title_length": len(title),
            },
        }

    def _load_soup(self, file_path: str) -> Optional[BeautifulSoup]:
        p = Path(file_path)
        if not p.exists():
            return None
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                return BeautifulSoup(f.read(), "html.parser")
        except Exception:
            return None

    def _inject_og_tags(self, soup: BeautifulSoup, title: str, description: str, keywords: List[str]):
        if not soup.head:
            return
        og_props = {
            "og:title": title[:60],
            "og:description": description[:155],
            "og:type": "website",
            "og:url": os.getenv("SEO_BASE_URL", "https://example.com"),
            "og:image": os.getenv("SEO_LOGO_URL", "https://example.com/logo.png"),
            "og:locale": "pt_BR",
        }
        existing = {m.get("property"): m for m in soup.head.find_all("meta", attrs={"property": True})}
        for prop, content in og_props.items():
            if prop in existing:
                existing[prop]["content"] = content
            else:
                tag = soup.new_tag("meta", attrs={"property": prop, "content": content})
                soup.head.append(tag)

    def _inject_schema_jsonld(self, soup: BeautifulSoup, title: str, description: str):
        schema = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title or os.getenv("SEO_BUSINESS_NAME", "Doutor Page"),
            "description": description or title,
            "url": os.getenv("SEO_BASE_URL", "https://example.com"),
            "inLanguage": "pt-BR",
        }
        script = soup.new_tag("script", attrs={"type": "application/ld+json"})
        script.string = json.dumps(schema, ensure_ascii=False)
        existing = soup.find("script", type="application/ld+json")
        if existing:
            existing.replace_with(script)
        elif soup.head:
            soup.head.append(script)

    def _calculate_score(self, word_count: int, images, missing_alt: int, broken_links: int, headings: dict, title: str) -> int:
        score = 0
        if 300 <= word_count <= 2000:
            score += 20
        elif word_count > 2000:
            score += 15
        if images:
            score += 10
        if missing_alt == 0:
            score += 10
        elif images and missing_alt < len(images) / 2:
            score += 5
        if broken_links == 0:
            score += 15
        elif broken_links == 1:
            score += 5
        if headings.get("h1") == 1:
            score += 10
        if headings.get("h2", 0) > 0:
            score += 5
        if 30 <= len(title) <= 60:
            score += 15
        elif len(title) > 0:
            score += 5
        return min(score, 100)

    def _generate_seo_recommendations(self, kw_in_title, kw_in_h1, density, kw_in_alts, links, title) -> List[str]:
        recs = []
        if not kw_in_title:
            recs.append("Adicionar keyword no title tag")
        if not kw_in_h1:
            recs.append("Adicionar keyword no H1")
        if density < 0.5:
            recs.append("Aumentar densidade da keyword para 1-3%")
        elif density > 5:
            recs.append("Reduzir densidade da keyword (risco de keyword stuffing)")
        if links and kw_in_alts == 0:
            recs.append("Adicionar alt text com keyword em imagens")
        if len(title) < 30:
            recs.append("Aumentar title para mínimo 30 caracteres")
        elif len(title) > 60:
            recs.append("Reduzir title para máximo 60 caracteres")
        if not recs:
            recs.append("SEO otimizado — nenhuma recomendação necessária")
        return recs
