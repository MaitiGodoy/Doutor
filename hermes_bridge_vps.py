#!/usr/bin/env python3
"""HermesBridge VPS edition - lightweight, direct Ollama calls"""
import asyncio, json, logging, os, base64
logger = logging.getLogger('doutor.hermes')

class HermesBridge:
    def __init__(self):
        self.call_count = 0
        self.ollama_base = os.environ.get("OLLAMA_BASE", "http://localhost:11434")
        self.ollama_model = os.environ.get("OLLAMA_MODEL", "hermes3:8b")

    async def _ask_ollama(self, system, prompt, temperature=0.3):
        self.call_count += 1
        payload = {
            "model": self.ollama_model,
            "prompt": f"{system}\n\n{prompt}",
            "stream": False,
            "options": {"temperature": temperature, "num_predict": 2048}
        }
        try:
            import urllib.request
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{self.ollama_base}/api/generate",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            resp = urllib.request.urlopen(req, timeout=120)
            result = json.loads(resp.read().decode())
            return {
                "status": "ok",
                "response": result.get("response", ""),
                "model": result.get("model", self.ollama_model),
                "via": "ollama"
            }
        except Exception as e:
            return {"status": "error", "error": str(e), "via": "ollama"}

    async def participate_execution(self, task, context):
        return await self._ask_ollama(
            "You are Hermes Agent integrated into Doutor v5.0.",
            f"Task: {json.dumps(task)}\nContext: {json.dumps(context)[:500]}"
        )

    async def participate_council(self, briefing, plan):
        return await self._ask_ollama(
            "You are a council member. Vote approve/deny with reasoning.",
            f"Briefing: {json.dumps(briefing)[:500]}\nPlan: {json.dumps(plan)[:500]}"
        )

    async def participate_seo_generation(self, topic, context=""):
        return await self._ask_ollama(
            "You are an SEO specialist. Suggest improvements.",
            f"Topic: {topic}\nContext: {context}"
        )

    async def participate_growth_analysis(self, data, analysis_type="market"):
        return await self._ask_ollama(
            "You are a growth analyst. Provide insights.",
            f"Data: {json.dumps(data)[:500]}\nType: {analysis_type}"
        )

    async def get_status(self):
        return {"model": self.ollama_model, "provider": "ollama", "via": "api"}

    def get_stats(self):
        return {"call_count": self.call_count}
