import os, json, time, asyncio, logging
from pathlib import Path
from typing import Dict, Optional
from agents.base_agent import BaseAgent

logger = logging.getLogger("doutor.zoiao")

class ZoiaoAgent(BaseAgent):
    def __init__(self, config: Dict, router):
        super().__init__("the_zoiao", config, router)
        self.headless = config.get("safety", {}).get("headless", True)
        self.timeout = config.get("safety", {}).get("timeout_sec", 15)
        self.max_actions = config.get("safety", {}).get("max_actions_per_turn", 5)
        self.log_path = Path(config.get("log_path", "logs/zoiao_browser.jsonl"))
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    async def navigate_and_extract(self, url: str, selector: str = "", extraction_type: str = "text") -> Dict:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return {"status": "fail", "error": "playwright_not_installed", "install_cmd": "pip install playwright && playwright install"}

        start = time.time()
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    viewport={"width": 1280, "height": 720}
                )
                page = await context.new_page()
                await page.goto(url, wait_until="networkidle", timeout=self.timeout * 1000)

                if selector:
                    await page.wait_for_selector(selector, timeout=self.timeout * 1000)

                if extraction_type == "text":
                    data = await page.text_content(selector) if selector else await page.content()
                elif extraction_type == "json":
                    raw = await page.locator(selector).inner_text() if selector else await page.content()
                    data = json.loads(raw) if raw.strip().startswith("{") else raw
                elif extraction_type == "screenshot":
                    cache_dir = Path("cache")
                    cache_dir.mkdir(exist_ok=True)
                    path = str(cache_dir / f"zoiao_{int(time.time())}.png")
                    await page.screenshot(path=path, full_page=False)
                    data = path
                elif extraction_type == "html":
                    data = await page.content()
                elif extraction_type == "attributes":
                    hrefs = await page.locator(selector).evaluate_all("els => els.map(el => el.outerHTML)") if selector else []
                    data = hrefs
                else:
                    data = await page.content()

                await browser.close()

                result = {"status": "success", "url": url, "data_length": len(str(data)) if isinstance(data, str) else 1, "execution_time_ms": int((time.time() - start) * 1000), "actions_taken": 1}
                self._log(result)
                return result
        except asyncio.TimeoutError:
            err = {"status": "fail", "error": "timeout", "url": url, "execution_time_ms": self.timeout * 1000}
            self._log(err)
            return err
        except Exception as e:
            err = {"status": "fail", "error": str(e), "url": url}
            self._log(err)
            return err

    async def execute_browser_task(self, objective: str, context: Optional[Dict] = None) -> Dict:
        prompt = f"Objetivo: {objective}\nContexto: {json.dumps(context, default=str)[:500] if context else 'None'}\nExtraia URL, seletor e tipo de extração. Retorne JSON com 'url', 'selector', 'extraction_type'."
        result = await self.execute(prompt, force_chronic=False)
        parsed = self._safe_json_parse(result.get("response", {}).get("content", "{}"))
        url = parsed.get("url", "")
        if not url:
            return {"status": "fail", "error": "no_url_in_objective", "objective": objective[:200]}
        return await self.navigate_and_extract(url, parsed.get("selector", ""), parsed.get("extraction_type", "text"))

    def _log(self, data: Dict):
        entry = {"timestamp": time.time(), "status": data.get("status"), "url": data.get("url"), "error": data.get("error"), "time_ms": data.get("execution_time_ms")}
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

# EOF
