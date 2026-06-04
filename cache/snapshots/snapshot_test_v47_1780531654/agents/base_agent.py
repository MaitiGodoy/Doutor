import os
import json
import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from kernel.provider_router import ProviderRouter

logger = logging.getLogger("doutor.base_agent")

# the_chronic — injects chaotic creativity into every agent prompt
CHRONIC_INJECTION = (
    "[OBSERVAÇÃO DO CHRONIC]: Pensa fora da caixa, caralho! "
    "Se o plano tá muito quadrado, joga ele no liquidificador. "
    "Adiciona um plot twist, uma inversão de expectativa, um elemento caótico que faça sentido. "
    "Mas não viaja — mantém o pé no resultado. Quero algo que funcione E surpreenda."
)


class BaseAgent:
    def __init__(self, role: str, config: Dict, router: ProviderRouter = None):
        self.role = role
        self.config = config
        self.router = router or ProviderRouter()
        self.max_retries = config.get("max_retries", 2)
        self.timeout = config.get("timeout", 120)
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2048)
        self.model = config.get("model", "qwen-2.5-coder-7b-instruct")
        self.fallback_model = config.get("fallback_model", "gemma-2-9b")
        self.system_prompt_file = config.get("system_prompt_file", "")
        self.audit_log = Path(config.get("log_to", f"logs/{role}_audit.jsonl"))
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)

    def _load_system_prompt(self) -> str:
        if self.system_prompt_file:
            p = Path(self.system_prompt_file)
            if not p.is_absolute():
                p = Path(__file__).parent.parent / self.system_prompt_file
            if p.exists():
                try:
                    return p.read_text(encoding="utf-8")
                except Exception as e:
                    logger.warning(f"Failed to load system prompt {p}: {e}")
        return f"You are {self.role}. Respond exclusively in valid JSON."

    def inject_chronic(self, prompt: str) -> str:
        return prompt + "\n\n" + CHRONIC_INJECTION

    def _safe_json_parse(self, text: str) -> Dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            start = next((i for i, l in enumerate(lines) if l.startswith("```")), 0)
            end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("```")), len(lines))
            text = "\n".join(lines[start + 1:end])
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            import re
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            return {"status": "error", "raw_output": text[:500], "note": "failed_json_parse"}

    def _log_execution(self, entry: Dict):
        try:
            with open(self.audit_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass

    async def execute(self, user_input: str, context: str = "", force_chronic: bool = True) -> Dict:
        start = time.time()
        system = self._load_system_prompt()
        prompt = user_input
        if context:
            prompt = f"Context: {context}\n\nTask: {user_input}"
        if force_chronic:
            prompt = self.inject_chronic(prompt)

        entry = {"timestamp": start, "role": self.role, "status": "pending", "input_preview": user_input[:200]}

        for attempt in range(1 + self.max_retries):
            try:
                model = self.model if attempt == 0 else self.fallback_model
                result_text = await asyncio.wait_for(
                    self._call_llm(system, prompt, model),
                    timeout=self.timeout
                )
                result = self._safe_json_parse(result_text)
                elapsed = time.time() - start
                entry["status"] = "success"
                entry["attempt"] = attempt
                entry["model_used"] = model
                entry["elapsed_ms"] = int(elapsed * 1000)
                entry["output_preview"] = str(result)[:200]
                self._log_execution(entry)
                result["_meta"] = {
                    "role": self.role,
                    "model": model,
                    "attempt": attempt,
                    "elapsed_ms": int(elapsed * 1000),
                    "chronic_injected": force_chronic,
                }
                return result
            except asyncio.TimeoutError:
                logger.warning(f"[{self.role}] Timeout on attempt {attempt}")
                entry["attempt"] = attempt
                entry["error"] = "timeout"
            except Exception as e:
                logger.warning(f"[{self.role}] Attempt {attempt} failed: {e}")
                entry["attempt"] = attempt
                entry["error"] = str(e)

        entry["status"] = "failed"
        entry["error"] = "all_retries_exhausted"
        self._log_execution(entry)
        return {
            "status": "error",
            "role": self.role,
            "error": "All retries exhausted",
            "_meta": {"role": self.role, "attempts": 1 + self.max_retries, "elapsed_ms": int((time.time() - start) * 1000)},
        }

    async def _call_llm(self, system: str, prompt: str, model: str = None) -> str:
        from kernel.llm_client import call_llm
        result = await call_llm(self.role, system, prompt)
        if isinstance(result, dict):
            return result.get("content", result.get("text", json.dumps(result)))
        return str(result)
