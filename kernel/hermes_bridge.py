"""
╔══════════════════════════════════════════════════════════════╗
║         HERMES BRIDGE — Doutor v5.0 Integração              ║
║                                                              ║
║   Ponte que conecta o Doutor ao Hermes Agent na VPS,         ║
║   permitindo que Hermes participe ativamente de TODAS        ║
║   as etapas do pipeline:                                     ║
║     • Council (votação)                                      ║
║     • Planning (plano alternativo)                           ║
║     • Code Review (auditoria de código)                      ║
║     • Quality Gates (avaliação de qualidade)                 ║
║     • SEO (geração de conteúdo)                              ║
║     • Growth (análise de mercado)                            ║
║     • Ethics (validação ética)                               ║
║                                                              ║
║   Hermes APRENDE a cada chamada — skills, memória,           ║
║   sessões são acumuladas dentro do container.                ║
╚══════════════════════════════════════════════════════════════╝
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger("doutor.hermes_bridge")

# ─── CONFIGURAÇÃO DA VPS ─────────────────────────────────────
VPS_HOST = os.getenv("HERMES_VPS_HOST", "2.24.71.246")
VPS_USER = os.getenv("HERMES_VPS_USER", "root")
VPS_SSH_KEY = os.getenv("HERMES_SSH_KEY", "C:/Users/User/.ssh/hostinger_vps.pem")
HERMES_CONTAINER = os.getenv("HERMES_CONTAINER", "hermes")
OLLAMA_BASE = os.getenv("HERMES_OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("HERMES_MODEL", "hermes3:8b")


class HermesBridge:
    """
    Ponte Doutor ↔ Hermes Agent.

    Usa duas vias de comunicação:
    1. API Ollama (OpenAI-compatible) → chamadas one-shot rápidas
    2. SSH + Docker CLI → comandos Hermes (skills, memória, sessões)
    """

    def __init__(self):
        self.call_count = 0
        self.participation_log: List[Dict] = []
        self._ssh_available = self._check_ssh()

    def _check_ssh(self) -> bool:
        """Verifica se SSH está disponível"""
        try:
            import shutil
            return shutil.which("ssh") is not None
        except Exception:
            return False

    # ═══════════════════════════════════════════════════════════
    # VIA 1: API OLLAMA (one-shot, rápido, confiável)
    # ═══════════════════════════════════════════════════════════

    async def _ask_ollama(self, system: str, prompt: str, temperature: float = 0.3) -> Dict:
        """
        Chama Hermes3 via API Ollama na VPS.
        Usa SSH + Python script remoto para evitar problemas de quoting.
        """
        self.call_count += 1
        full_prompt = f"{system}\n\n{prompt}"
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": 2048
            }
        }

        # Gera script Python temporário no VPS
        import tempfile, base64 as b64mod
        # Codifica o payload em base64 para evitar problemas de quoting
        payload_b64 = b64mod.b64encode(json.dumps(payload).encode()).decode()
        script = f"""#!/usr/bin/env python3
import urllib.request, json, sys, base64
data = json.loads(base64.b64decode('{payload_b64}').decode())
req = urllib.request.Request(
    '{OLLAMA_BASE}/api/generate',
    data=json.dumps(data).encode(),
    headers={{"Content-Type": "application/json"}}
)
try:
    resp = urllib.request.urlopen(req, timeout=120)
    print(resp.read().decode())
except Exception as e:
    print(json.dumps({{"error": str(e)}}), file=sys.stderr)
    sys.exit(1)
"""
        # Codifica script em base64 para evitar problemas de escaping
        import base64, tempfile, os
        script_b64 = base64.b64encode(script.encode()).decode()

        # Grava script num arquivo temporário no VPS, executa, depois limpa
        remote_script_path = f"/tmp/hermes_ollama_{os.getpid()}.py"

        # Passo 1: escrever script via base64 echo
        write_cmd = [
            "ssh", "-i", VPS_SSH_KEY,
            "-o", "StrictHostKeyChecking=no",
            "-o", "ConnectTimeout=10",
            f"{VPS_USER}@{VPS_HOST}",
            f"echo {script_b64} | base64 -d > {remote_script_path} && python3 {remote_script_path} && rm -f {remote_script_path}"
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *write_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=130)
            output = stdout.decode("utf-8", errors="replace").strip()
            err = stderr.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                return {"status": "error", "error": err[:500], "via": "ollama"}

            result = json.loads(output)
            return {
                "status": "ok",
                "response": result.get("response", ""),
                "model": result.get("model", OLLAMA_MODEL),
                "eval_count": result.get("eval_count", 0),
                "total_duration_ns": result.get("total_duration", 0),
                "via": "ollama"
            }
        except asyncio.TimeoutError:
            return {"status": "error", "error": "Ollama timed out after 120s", "via": "ollama"}
        except Exception as e:
            return {"status": "error", "error": str(e), "via": "ollama"}

    # ═══════════════════════════════════════════════════════════
    # VIA 2: HERMES CLI (skills, memória, sessões, gateway)
    # ═══════════════════════════════════════════════════════════

    async def _hermes_cli(self, args: str, timeout: int = 60) -> Dict:
        """
        Executa comando Hermes CLI via SSH + Docker.
        Ex: hermes skills list, hermes sessions list, hermes memory etc.
        """
        self.call_count += 1
        cmd = (
            f'ssh -i {VPS_SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=10 '
            f'{VPS_USER}@{VPS_HOST} '
            f'"docker exec {HERMES_CONTAINER} hermes {args}" 2>/dev/null'
        )

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            output = stdout.decode("utf-8", errors="replace").strip()
            err = stderr.decode("utf-8", errors="replace").strip()

            return {
                "status": "ok" if proc.returncode == 0 else "error",
                "output": output or err,
                "exit_code": proc.returncode,
                "via": "hermes_cli"
            }
        except asyncio.TimeoutError:
            return {"status": "error", "error": f"Hermes CLI timed out after {timeout}s", "via": "hermes_cli"}
        except Exception as e:
            return {"status": "error", "error": str(e), "via": "hermes_cli"}

    # ═══════════════════════════════════════════════════════════
    # PARTICIPAÇÃO EM CADA ETAPA DO PIPELINE
    # ═══════════════════════════════════════════════════════════

    async def participate_council(self, briefing: Dict, plan: Dict) -> Dict:
        """
        Hermes participa do CONSELHO (Council).
        Vota se o plano é viável, ético, e alinhado com objetivos.
        """
        self._log("council", "Hermes votando no Conselho...")

        system = "You are Hermes Agent, a member of the Doutor Council. You vote on plans with reasoning."
        prompt = f"""
As a council member, analyze this plan and vote:

BRIEFING: {json.dumps(briefing, ensure_ascii=False)[:2000]}
PLAN: {json.dumps(plan, ensure_ascii=False)[:2000]}

Respond in valid JSON ONLY with:
- vote: "approve" | "veto" | "abstain"
- reasoning: string explaining your vote
- concerns: array of strings with potential issues
- suggestions: array of strings with improvements
"""
        result = await self._ask_ollama(system, prompt, temperature=0.2)
        self._log("council", f"Hermes votou: {result.get('response', 'erro')[:100]}")
        return result

    async def participate_planning(self, briefing: Dict, plan_a: Dict, plan_b: Dict) -> Dict:
        """
        Hermes como PLANNER alternativo.
        Gera um plano C baseado no briefing, oferecendo perspectiva diferente.
        """
        self._log("planning", "Hermes gerando plano alternativo...")

        system = "You are Hermes Agent, an alternative planner. Generate concise, actionable plans."
        prompt = f"""
You have seen Planner Alpha's plan and Planner Beta's plan.
Now generate a THIRD option (Plan C) that combines the best of both.

BRIEFING: {json.dumps(briefing, ensure_ascii=False)[:2000]}
PLAN A: {json.dumps(plan_a, ensure_ascii=False)[:1500]}
PLAN B: {json.dumps(plan_b, ensure_ascii=False)[:1500]}

Respond in valid JSON ONLY with:
- plan_c_summary: string with the combined approach
- key_differences: array of strings showing how it differs from A and B
- risk_level: "low" | "medium" | "high"
- strengths: array of strings
"""
        result = await self._ask_ollama(system, prompt, temperature=0.4)
        self._log("planning", f"Hermes gerou Plano C")
        return result

    async def participate_code_review(self, code: Dict, language: str = "python") -> Dict:
        """
        Hermes como CODE REVIEWER.
        Analisa código gerado pelos Devs e sugere melhorias.
        """
        self._log("code_review", "Hermes revisando código...")

        system = f"You are Hermes Agent, a senior {language} code reviewer. Be thorough and specific."
        prompt = f"""
Review this code and provide feedback:

CODE: {json.dumps(code, ensure_ascii=False)[:3000]}

Respond in valid JSON ONLY with:
- score: integer 0-100
- strengths: array of strings
- issues: array of {{severity, line, description, suggestion}}
- security_concerns: array of strings
- overall_verdict: "approve" | "changes_requested" | "rejected"
"""
        result = await self._ask_ollama(system, prompt, temperature=0.1)
        self._log("code_review", f"Hermes score: {result.get('response', '?')[:60]}")
        return result

    async def participate_quality_gate(self, output: Dict, gate_type: str = "quality") -> Dict:
        """
        Hermes como GATE DE QUALIDADE.
        Avalia output antes de prosseguir no pipeline.
        """
        self._log(f"quality_gate_{gate_type}", "Hermes avaliando qualidade...")

        system = "You are Hermes Agent, a quality assurance auditor. Be strict and precise."
        prompt = f"""
Evaluate this {gate_type} output for quality and correctness:

OUTPUT: {json.dumps(output, ensure_ascii=False)[:3000]}

Respond in valid JSON ONLY with:
- quality_score: float 0.0-1.0
- passed: boolean
- issues_found: array of strings
- recommendations: array of strings
- critical_failures: array of strings (if any)
"""
        result = await self._ask_ollama(system, prompt, temperature=0.15)
        self._log("quality_gate", f"Hermes quality: {result.get('response', '?')[:60]}")
        return result

    async def participate_seo_generation(self, topic: str, context: str = "") -> Dict:
        """
        Hermes como GERADOR SEO.
        Contribui com conteúdo para blogs/notícias.
        """
        self._log("seo_generation", "Hermes gerando conteúdo SEO...")

        system = "You are Hermes Agent, a skilled SEO content writer in Brazilian Portuguese."
        prompt = f"""
Write SEO-optimized content about: {topic}
Context: {context or "General audience"}
Style: Informative, engaging, optimized for search

Respond in valid JSON ONLY with:
- title: string
- meta_description: string (max 160 chars)
- key_points: array of 3-5 strings
- suggested_headings: array of 3-5 strings
- target_keywords: array of 5-8 strings
"""
        result = await self._ask_ollama(system, prompt, temperature=0.5)
        self._log("seo_generation", f"Hermes gerou SEO para: {topic[:50]}")
        return result

    async def participate_growth_analysis(self, data: Dict, analysis_type: str = "market") -> Dict:
        """
        Hermes como ANALISTA DE CRESCIMENTO.
        Analisa dados de mercado, competidores, tendências.
        """
        self._log(f"growth_{analysis_type}", "Hermes analisando mercado...")

        system = "You are Hermes Agent, a growth and market intelligence analyst."
        prompt = f"""
Analyze this {analysis_type} data and provide strategic insights:

DATA: {json.dumps(data, ensure_ascii=False)[:3000]}

Respond in valid JSON ONLY with:
- key_insights: array of strings
- opportunities: array of {{opportunity, impact, effort}}
- threats: array of strings
- recommendations: array of {{action, priority, expected_outcome}}
"""
        result = await self._ask_ollama(system, prompt, temperature=0.4)
        self._log("growth_analysis", "Hermes completou análise de crescimento")
        return result

    async def participate_ethics_audit(self, action: str, context: Dict) -> Dict:
        """
        Hermes como AUDITOR DE ÉTICA.
        Valida ações contra princípios éticos e LGPD.
        """
        self._log("ethics_audit", "Hermes auditando ética...")

        system = "You are Hermes Agent, an ethics and compliance auditor for Brazilian regulations (LGPD)."
        prompt = f"""
Audit this action for ethical compliance:

ACTION: {action}
CONTEXT: {json.dumps(context, ensure_ascii=False)[:2000]}

Respond in valid JSON ONLY with:
- ethical_status: "approved" | "flagged" | "rejected"
- risk_level: "low" | "medium" | "high" | "critical"
- lgpd_violations: array of strings (if any)
- recommendations: array of strings
- final_verdict: string
"""
        result = await self._ask_ollama(system, prompt, temperature=0.2)
        self._log("ethics_audit", f"Hermes ethics: {result.get('response', '?')[:60]}")
        return result

    async def participate_execution(self, task: str, context: Dict) -> Dict:
        """
        Hermes como EXECUTOR DIRETO.
        Executa tarefas delegadas pelo Doutor.
        """
        self._log("execution", "Hermes executando tarefa...")

        system = "You are Hermes Agent, a general-purpose AI executor integrated with Doutor."
        prompt = f"""
Execute the following task:

TASK: {task}
CONTEXT: {json.dumps(context, ensure_ascii=False)[:2000]}

Respond with the result of your execution in valid JSON:
- status: "ok" | "error"
- result: string with the outcome
- details: object with additional information if applicable
"""
        result = await self._ask_ollama(system, prompt, temperature=0.3)
        self._log("execution", f"Hermes executou: {task[:50]}")
        return result

    async def learn_from_pipeline(self, pipeline_result: Dict) -> Dict:
        """
        Hermes APRENDE com o resultado do pipeline.
        Chama Hermes CLI para armazenar aprendizado em memória/skills.
        Isso faz com que Hermes acumule conhecimento a cada execução.
        """
        self._log("learning", "Hermes aprendendo com o pipeline...")

        # First, use Ollama to extract learning
        system = "You are Hermes Agent. Extract key learnings from this pipeline run."
        prompt = f"""
Extract learning points from this pipeline execution:

RESULT: {json.dumps(pipeline_result, ensure_ascii=False)[:3000]}

Respond in valid JSON ONLY with:
- key_learnings: array of strings (max 5)
- patterns_observed: array of strings (max 3)
- knowledge_to_remember: array of {{topic, detail}} (max 3)
"""
        learn_result = await self._ask_ollama(system, prompt, temperature=0.3)
        self._log("learning", f"Hermes extraiu aprendizados")

        # Then store in Hermes memory via CLI (if SSH available)
        if self._ssh_available:
            try:
                learning_data = learn_result.get("response", "{}")
                store_cmd = (
                    f'memory add --source=doutor_pipeline '
                    f'--content={json.dumps(learning_data)[:500]}'
                )
                await self._hermes_cli(store_cmd, timeout=30)
            except Exception:
                pass  # Non-blocking

        return learn_result

    # ═══════════════════════════════════════════════════════════
    # MÉTODOS DE SUPORTE
    # ═══════════════════════════════════════════════════════════

    async def get_status(self) -> Dict:
        """Retorna status completo do Hermes Agent na VPS"""
        containers = await self._hermes_cli("status", timeout=15)
        return {
            "agent": "hermes",
            "version": "0.15.1",
            "container": HERMES_CONTAINER,
            "host": VPS_HOST,
            "model": OLLAMA_MODEL,
            "ssh_available": self._ssh_available,
            "call_count": self.call_count,
            "containers": containers.get("output", ""),
            "participations": len(self.participation_log)
        }

    async def get_skills(self) -> Dict:
        """Lista skills instaladas no Hermes"""
        return await self._hermes_cli("skills list", timeout=15)

    async def get_sessions(self) -> Dict:
        """Lista sessões do Hermes"""
        return await self._hermes_cli("sessions list", timeout=15)

    def get_participation_history(self) -> List[Dict]:
        """Retorna histórico de participações do Hermes no pipeline"""
        return self.participation_log[-50:]  # Últimas 50

    def _log(self, stage: str, message: str):
        """Regista participação do Hermes"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "message": message
        }
        self.participation_log.append(entry)
        logger.info(f"[HermesB] {stage}: {message}")
