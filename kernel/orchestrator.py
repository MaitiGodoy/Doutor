import json, time, asyncio, os
from typing import Dict, List
from kernel.utils import load_state, save_state, hash_payload, validate_json
from kernel.agents import run_agent, run_neuro_copy
from kernel.config import FINANCIAL_GUARD, OPTIMIZATION
from kernel.concierge import concierge_explain
from kernel.notify import escalate_notification

class Orchestrator:
    def __init__(self, input_data: Dict):
        self.state = load_state()
        self.input = input_data
        self.run_id = self.state["run_id"]
        self.artifacts = self.state.get("artifacts", {})
        
    def detect_module(self) -> str:
        txt = json.dumps(self.input).lower()
        if any(k in txt for k in ["code", "func", "api", "debug", "test", "stack", "lint"]): return "programming"
        if any(k in txt for k in ["seo", "ads", "copy", "post", "funnel", "keywords", "ctr", "roas", "viral"]): return "marketing"
        if any(k in txt for k in ["infoproduto", "curso", "checkout", "lms", "lançamento", "afiliados", "pre-venda"]): return "infoproduct"
        return "multi"

    def build_dag(self) -> Dict:
        # Simple DAG: decompose multi-domain into subtasks
        return {
            "nodes": [
                {"id": "antimatter", "module": "programming", "task": "Automação/Script/API", "deps": []},
                {"id": "marketing", "module": "marketing", "task": "Copy/Ads/SEO", "deps": ["antimatter"]},
                {"id": "infoproduct", "module": "infoproduct", "task": "Checkout/LMS/Lançamento", "deps": ["marketing"]}
            ]
        }

    async def execute_node(self, node: Dict) -> Dict:
        role = "creator" if node["module"] in ["marketing", "infoproduct"] else "coder"
        result = await run_agent(role, node["task"], self.artifacts)
        self.artifacts[node["id"]] = result
        save_state({"run_id": self.run_id, "stage": node["id"], "artifacts": self.artifacts, "token_budget": self.state.get("token_budget", 0)})
        return result

    async def execute_dag(self, dag: Dict) -> Dict:
        for node in dag["nodes"]:
            if self.state.get("stage") == node["id"]: continue
            print(f"[DAG] Executando {node['id']}...")
            await self.execute_node(node)
        return self.artifacts

    def financial_guard_check(self, action: str, amount: float) -> Dict:
        if amount > FINANCIAL_GUARD["daily_spend_limit"]:
            return {"allowed": False, "reason": "Exceeds daily limit", "requires_human": True}
        return {"allowed": True, "reason": "OK", "requires_human": False}

    def dry_run_validation(self, deliverables: Dict) -> Dict:
        # Simulated validation
        return {
            "seo_score": 85.0,
            "policy_compliance": "pass",
            "predicted_ctr": 0.035,
            "predicted_cvr": 0.021,
            "viral_potential": 0.68,
            "recommendation": "deploy"
        }

    async def run(self) -> Dict:
        module = self.detect_module()
        if module == "multi":
            dag = self.build_dag()
            result = await self.execute_dag(dag)
        else:
            # Single module pipeline
            print(f"[PIPELINE] Iniciando módulo: {module}")
            # Planner A vs B
            a = asyncio.create_task(run_agent("planner_a", json.dumps(self.input)))
            b = asyncio.create_task(run_agent("planner_b", json.dumps(self.input)))
            pa, pb = await asyncio.gather(a, b)
            
            # Consensus (simplified)
            consensus = {"approach": pa.get("approach") or pb.get("approach"), "merged": {**pa, **pb}}
            self.artifacts["consensus"] = consensus
            
            # Creator/Producer
            if module in ["marketing", "infoproduct"]:
                neuro = await run_neuro_copy(json.dumps(consensus))
                self.artifacts["neuro_copy"] = neuro
            else:
                code = await run_agent("coder", json.dumps(consensus), consensus)
                self.artifacts["code"] = code
            
            # Auditor
            audit = await run_agent("auditor", json.dumps(self.artifacts), self.artifacts)
            self.artifacts["audit"] = audit
            
            # Dry-run & Guard
            guard = self.financial_guard_check("deploy", 0.0)
            dry = self.dry_run_validation(self.artifacts)
            
            result = {
                "metadata": {"run_id": self.run_id, "module": module, "consensus_rounds": 1},
                "deliverables": self.artifacts,
                "guardrails": {"financial": guard, "dry_run": dry},
                "status": "ready" if guard["allowed"] and dry["recommendation"] == "deploy" else "blocked"
            }
            
        save_state({"run_id": self.run_id, "stage": "COMPLETE", "artifacts": self.artifacts, "token_budget": self.state.get("token_budget", 0)})
        return result

    def check_escalation_triggers(self, current_state: dict) -> list:
        """Verifica se alguma regra de escalation foi acionada"""
        rules_path = "escalation_rules.json"
        if not os.path.exists(rules_path):
            return []
            
        with open(rules_path, "r", encoding="utf-8") as f:
            rules = json.load(f)["rules"]
        
        triggered = []
        for rule in rules:
            if self._evaluate_condition(rule["condition"], current_state):
                triggered.append(rule)
        return triggered
    
    def _evaluate_condition(self, condition: str, state: dict) -> bool:
        """Avalia condição simples (pode ser expandido para parser mais complexo)"""
        try:
            # Safe eval com namespace controlado
            safe_globals = {"__builtins__": {}}
            safe_locals = {**state, **FINANCIAL_GUARD}
            return eval(condition.lower(), safe_globals, safe_locals)
        except Exception as e:
            print(f"[Orchestrator] Error evaluating condition '{condition}': {e}")
            return False
    
    async def handle_escalation(self, rule: dict, context: dict) -> dict:
        """Processa uma regra de escalation acionada"""
        # 1. Gerar mensagem humana via Concierge
        concierge_msg = await concierge_explain(
            system_output={"rule": rule, "context": context},
            user_context=f"O sistema precisa da sua atenção sobre: {rule['trigger']}"
        )
        
        # 2. Enviar notificação pelo canal adequado
        notification = escalate_notification(
            priority=rule["priority"],
            message=concierge_msg["summary_pt"],
            requires_response=rule.get("requires_response", False)
        )
        
        # 3. Se requer resposta, retornar status de "waiting_response"
        if rule.get("requires_response"):
            return {
                "escalation_id": hash_payload(f"{rule['trigger']}_{time.time()}"),
                "status": "waiting_response",
                "notification": notification,
                "concierge_payload": concierge_msg,
                "timeout_at": time.time() + (rule.get("timeout_minutes", 60) * 60)
            }
        
        return {"status": "notified", "notification": notification}
    
    async def run_with_concierge(self) -> dict:
        """Wrapper do run() que integra Concierge e Notifications"""
        result = await self.run()
        
        # Sempre explicar o resultado para o usuário via Concierge
        explanation = await concierge_explain(result)
        
        # Verificar se precisa escalar
        escalations = self.check_escalation_triggers({**result, **self.artifacts})
        escalation_results = []
        for rule in escalations:
            esc_res = await self.handle_escalation(rule, {**result, **self.artifacts})
            escalation_results.append(esc_res)
        
        return {
            "system_output": result,
            "human_explanation": explanation,
            "escalations": escalation_results
        }
