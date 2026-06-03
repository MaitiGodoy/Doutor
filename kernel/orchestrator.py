import asyncio
import os
import time
import random
from typing import Dict, Any

class AntimatterOrchestrator:
    def __init__(self, agent_configs: Dict, provider_router):
        self.agent_configs = agent_configs
        self.provider_router = provider_router
        self.agents = {}
        self.state_mgr = None  # Placeholder for state manager
        self.token_mgr = None  # Placeholder for token manager

    async def initialize(self):
        # Initialize agents
        for role, config in self.agent_configs.items():
            if role == "the_minimalist":
                from agents.minimalist_agent import MinimalistAgent
                self.agents[role] = MinimalistAgent(config, self.provider_router)
            elif role == "the_gossip":
                from agents.gossip_agent import GossipAgent
                self.agents[role] = GossipAgent(config, self.provider_router)
            # Other agents would be initialized here, but we are only concerned with the_minimalist and the_gossip
            # For the sake of this example, we'll assume other agents are imported and initialized similarly.
            # In a real scenario, you would have more agent initializations.
            pass
         
        # Initialize the Council Protocol after agents are ready
        from agents.protocols.council_protocol import CouncilProtocol
        self.council = CouncilProtocol(self.agents, self.state_mgr)
        
        # Initialize the Evolution Engine after agents are ready
        from kernel.evolution_engine import EvolutionEngine
        self.evolution_engine = EvolutionEngine(self.agents, self.state_mgr)

    async def execute(self, input_data: Dict) -> Dict:
        start_time = time.time()
        # We assume the execution is divided into phases.
        # For simplicity, we'll define a list of phase names.
        phases = ["Briefing", "Estratégia", "Planejamento", "Execução", "Revisão"]
        executed_phases = []
        governance_log = []  # Placeholder for governance decisions
        
        # --- INÍCIO DO PROTOCOLO CONSELHO ---
        # Run the council round before any phase
        council_result = await self.council.run_council_round(input_data)
        input_data["council_wisdom"] = council_result["synthesis"]
        input_data["all_opinions"] = council_result["opinions"]

        print(f"[CONSELHO] Consenso: {council_result['consensus']}. {len(council_result['opinions'])} agentes opinaram.")
        # --- FIM DO PROTOCOLO CONSELHO ---

        for i, current_phase_name in enumerate(phases):
            executed_phases.append(current_phase_name.lower())
            # --- INÍCIO DA INTEGRAÇÃO THE MINIMALIST ---
            if hasattr(self, 'agents') and 'the_minimalist' in self.agents:
                minimalist = self.agents['the_minimalist']
                task_desc = f"Fase: {current_phase_name}. Objetivo: {input_data.get('primary_goal', '')}"
                
                opt_result = await minimalist.evaluate_optimization(task_desc, input_data)
                
                if opt_result.get("optimization") != "none" and opt_result.get("risk_level") == "low":
                    # Valida com The Constitution se necessário
                    if opt_result.get("requires_governance_check"):
                        # Assuming there is an agent named 'the_constitution'
                        if 'the_constitution' in self.agents:
                            const_check = await self.agents['the_constitution'].execute(
                                user_input=f"Aprove esta otimização: {opt_result['optimization']}",
                                force_chronic=False
                            )
                            # Parse simples para verificar aprovação (assumindo que Constitution retorna approved: bool)
                            if "approved" in const_check['response']['content'].lower() and "true" in const_check['response']['content'].lower():
                                input_data = await minimalist.apply_optimization(input_data, opt_result['implementation_hint'])
                                print(f"[Minimalist] Otimização aplicada: {opt_result['optimization']}")
                        else:
                            # If Constitution agent is not available, we skip governance check? But the rule says requires_governance_validation: true.
                            # For safety, we skip the optimization if we can't validate.
                            pass
                    else:
                        input_data = await minimalist.apply_optimization(input_data, opt_result['implementation_hint'])
                        print(f"[Minimalist] Otimização aplicada: {opt_result['optimization']}")
            # --- FIM DA INTEGRAÇÃO THE MINIMALIST ---

            # Here we would call the actual phase logic with the (possibly) optimized input_data
            # For the sake of this example, we'll just pass the input_data to the next phase.
            # In a real orchestrator, you would have specific logic for each phase.
            # We'll simulate by doing nothing and just moving to the next phase.

        # After all phases, we have a final result (for now, just the input_data)
        final_result = input_data
        
        # --- INÍCIO DA INTEGRAÇÃO A FOFOQUEIRA ---
        if hasattr(self, 'agents') and 'the_gossip' in self.agents:
            gossip = self.agents['the_gossip']
            
            # Prepara contexto completo para a narrativa
            pipeline_log = {
                "input": input_data,
                "output": final_result,
                "started_at": start_time,
                "ended_at": time.time()
            }
            
            # Pega audit trail do StateManager (placeholder)
            # In a real implementation, we would get this from self.state_mgr
            audit_trail = []  # Placeholder
            
            # Métricas consolidadas
            metrics = {
                "tokens_used": self.token_mgr.get_total_used() if self.token_mgr else 0,
                "execution_time_ms": int((time.time() - start_time) * 1000),
                "phases_completed": len(executed_phases),
                "governance_approvals": len([g for g in governance_log if g.get("approved")]),
                "output_artifacts": []  # Placeholder for output artifacts
            }
            
            # Gera narrativa
            narrative = await gossip.narrate_pipeline(pipeline_log, audit_trail, metrics)
            
            # Anexa narrativa ao resultado final (para Concierge/MCP)
            final_result["gossip_narrative"] = narrative
            
            # Envia para usuário se configurado
            if os.getenv("NOTIFY_ON_COMPLETION_ONLY") == "true" and os.getenv("USER_PHONE"):
                await gossip.send_to_concierge(narrative, os.getenv("USER_PHONE"))
            
            print(f"[Fofoqueira] Narrativa gerada. Preview: {narrative['narrative_markdown'][:150]}...")
        # --- FIM DA INTEGRAÇÃO A FOFOQUEIRA ---
        
        # --- INÍCIO DO LOOP EVOLUTIVO (Raro, não toda vez para economizar) ---
        # 5% de chance de rodar evolução a cada task
        if random.random() < 0.05:
            # Escolhe um agente aleatório para tentar otimizar
            agent_to_optimize = random.choice(list(self.agents.keys()))
            if agent_to_optimize != 'the_darwin':
                await self.evolution_engine.run_evolution_cycle(agent_to_optimize)
        # --- FIM DO LOOP EVOLUTIVO ---

        # After all phases, return the result
        return final_result