import os, json, time
from pathlib import Path
from agents.darwin_agent import DarwinAgent

class EvolutionEngine:
    def __init__(self, agents: Dict, state_mgr):
        self.agents = agents
        self.state_mgr = state_mgr
        self.darwin = agents.get("the_darwin")
        self.quarantine_dir = Path("cache/quarantine_prompts")
        self.quarantine_dir.mkdir(exist_ok=True)

    async def run_evolution_cycle(self, agent_name: str):
        """Rodar ciclo de evolução para um agente específico."""
        if not self.darwin: 
            return

        # 1. Coletar logs recentes do agente
        logs = await self.state_mgr.get_agent_logs(agent_name, limit=50)
        config_path = f"agents/roles/{agent_name.replace('the_', '')}.json"
        
        if not os.path.exists(config_path): 
            return
        with open(config_path, 'r') as f: 
            current_config = json.load(f)

        # 2. Pedir mutação ao Darwin
        mutation = await self.darwin.analyze_and_mutate(logs, current_config)
        
        if mutation.get("error"): 
            return

        # 3. Aplicar mutação em "Quarentena" (Arquivo separado para teste A/B)
        test_config = {**current_config}
        if "new_prompt_section" in mutation:
            # Adiciona instrução ao prompt existente ou sobrescreve
            # We are not actually modifying the prompt file here, just storing the config for testing.
            # In a real system, we would create a new prompt file or modify the existing one.
            # For now, we just save the mutated config.
            test_config["system_prompt_file"] = current_config.get("system_prompt_file", "")
            # Salva versão mutante
            mutant_path = self.quarantine_dir / f"{agent_name}_mutant_v{int(time.time())}.json"
            with open(mutant_path, 'w') as f: 
                json.dump(test_config, f, indent=2)
            
            print(f"[DARWIN] Mutação gerada para {agent_name}. Arquivada em {mutant_path}")
            print(f"[DARWIN] Economia estimada: {mutation.get('estimated_savings_pct')}%")

            # Log the mutation
            self.darwin._log_mutation(mutation)
            return mutant_path
        return None