import os
import json
import time
import difflib
from pathlib import Path
from typing import Dict, List, Optional, Any
from agents.base_agent import BaseAgent

DESKTOP_PROMPT = """Gere HTML/CSS/JS completo para DESKTOP (largura mínima 1024px).
- Layout responsivo mas otimizado para telas grandes
- Grid/multi-coluna, navegação horizontal, hover states
- Tipografia maior, espaçamento generoso
- CTA visível sem scroll (above the fold)
- Retorne APENAS JSON com {"file": "index.html", "content": "..."}
"""

MOBILE_PROMPT = """Gere HTML/CSS/JS completo para MOBILE (largura máxima 480px).
- Layout single-column, touch-friendly (alvo de toque mínimo 48px)
- Navegação hamburger ou bottom nav
- Tipografia legível em mobile (mínimo 16px)
- CTA full-width, sticky se necessário
- Otimizado para Core Web Vitals (LCP < 2.5s, CLS < 0.1)
- Retorne APENAS JSON com {"file": "mobile.html", "content": "..."}
"""


class DualOutputAgent(BaseAgent):
    def __init__(self, config: Dict = None, router=None):
        super().__init__("the_producer", config or {}, router)
        self.output_dir = Path("output/html")

    def _build_prompt(self, variant: str, content_spec: Dict) -> str:
        spec_json = json.dumps(content_spec, indent=2, ensure_ascii=False)
        if variant == "desktop":
            return f"{DESKTOP_PROMPT}\n\nContent Spec:\n{spec_json}"
        return f"{MOBILE_PROMPT}\n\nContent Spec:\n{spec_json}"

    def _parse_output(self, raw: Dict) -> Dict:
        content = raw.get("content", raw.get("result", {}).get("content", ""))
        if isinstance(content, str):
            return {"content": content}
        if isinstance(content, dict):
            return content
        return {"content": str(content)}

    def _check_consistency(self, desktop: Dict, mobile: Dict) -> Dict:
        issues = []
        d_content = desktop.get("content", "")
        m_content = mobile.get("content", "")

        d_text = d_content.lower()
        m_text = m_content.lower()

        key_elements = ["cta", "button", "href", "https://", "mailto:"]
        for elem in key_elements:
            in_d = elem in d_text
            in_m = elem in m_text
            if in_d and not in_m:
                issues.append({"element": elem, "detail": f"Present in desktop but missing in mobile", "severity": "medium"})
            if in_m and not in_d:
                issues.append({"element": elem, "detail": f"Present in mobile but missing in desktop", "severity": "medium"})

        d_links = d_text.count("href=")
        m_links = m_text.count("href=")
        if abs(d_links - m_links) > 2:
            issues.append({"element": "links", "detail": f"Link count mismatch: desktop={d_links}, mobile={m_links}", "severity": "low"})

        return {
            "consistent": len(issues) == 0,
            "issues": issues,
            "desktop_size_chars": len(d_content),
            "mobile_size_chars": len(m_content),
            "desktop_size_kb": round(len(d_content) / 1024, 1),
            "mobile_size_kb": round(len(m_content) / 1024, 1),
        }

    async def generate_dual_output(self, content_spec: Dict, target_dir: str = None) -> Dict:
        start = time.time()
        if target_dir:
            self.output_dir = Path(target_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        desktop_raw = await self._build_and_execute("desktop", content_spec)
        mobile_raw = await self._build_and_execute("mobile", content_spec)

        desktop = self._parse_output(desktop_raw)
        mobile = self._parse_output(mobile_raw)

        consistency = self._check_consistency(desktop, mobile)

        desktop_path = self.output_dir / "index.html"
        mobile_path = self.output_dir / "mobile.html"

        if desktop.get("content"):
            desktop_path.write_text(desktop["content"], encoding="utf-8")
        if mobile.get("content"):
            mobile_path.write_text(mobile["content"], encoding="utf-8")

        result = {
            "status": "success",
            "files": {
                "desktop": str(desktop_path) if desktop.get("content") else None,
                "mobile": str(mobile_path) if mobile.get("content") else None,
            },
            "consistency": consistency,
            "elapsed_ms": int((time.time() - start) * 1000),
        }
        self._log_execution({"mode": "generate_dual_output", "result": result})
        return result

    async def _build_and_execute(self, variant: str, content_spec: Dict) -> Dict:
        prompt = self._build_prompt(variant, content_spec)
        return await self.execute(prompt)
