# 🔍 DIAGNÓSTICO ESTRUTURAL — DOUTOR v5.1 — AGENTES

## 📊 RESUMO DAS 4 FRENTES
| Frente | Arquivos Novos | Métodos Implementados | Integração com Kernel | Status |
|--------|----------------|----------------------|----------------------|--------|
| Substituição (A1-A8) | 1 (warden_agent.py) | pre_execution_check, post_commit_audit | ✅ Usa BaseAgent → provider_router, guards via AntiEntropy | ⚠️ Criado mas não integrado |
| SEO Content Suite | 0 (diretório vazio) | — | ❌ Não existe agents/content/seo_content_suite.py | ❌ Antigo ainda ativo (seo_orchestrator no kernel) |
| GEO Guru | 9 (orchestrator + 8 agents) | execute_mission (10 fases), extract, build, validate, generate, audit, inject, measure | ❌ Standalone — não usa provider_router, guards, sandbox | ⚠️ Criado mas não integrado |
| Agente Autônomo | 5 arquivos (todos vazios) | 0 — agent_loop.py vazio | ❌ Não existe implementação | ❌ Não implementado |

---

## ✅ AGENTES SUBSTITUÍDOS COM SUCESSO
| Agente Antigo | Novo Arquivo/Classe | Métodos Funcionais | Observação |
|---------------|---------------------|-------------------|------------|
| (Nenhum substituído) | WardenAgent (agents/warden_agent.py) | pre_execution_check, post_commit_audit | Novo agente de governança; **não substituiu nenhum agente antigo** — convive com ConstitutionAgent + SurgeonAgent em agents/governance.py |

---

## ⚠️ AGENTES PARCIAIS / PROBLEMAS DE INTEGRAÇÃO
| Arquivo/Classe | Problema Exato | Impacto | Correção Necessária |
|----------------|----------------|---------|---------------------|
| agents/warden_agent.py | Não registrado no orchestrator.py; não há hook de inicialização | Warden nunca é chamado automaticamente | Adicionar em orchestrator.py + hook pre-flight |
| kernel/geo_guru/ (8 agents + orchestrator) | Classes standalone — **não herdam BaseAgent**; usam aiohttp direto, regex, BeautifulSoup; **não chamam provider_router, guards, sandbox** | Duplicação de lógica LLM; sem quota/circuit breaker; sem validação de input/output; execução não isolada | Refatorar para herdar BaseAgent OU injetar router/guards/sandbox via construtor |
| kernel/autonomy/core/agent_loop.py | **Arquivo vazio (0 linhas)** | Loop autônomo inexistente | Implementar _cycle, _perceive, _act, _reflect, _escalate |
| agents/content/ | **Diretório vazio** | SEO Content Suite não existe como agente | Criar seo_content_suite.py com audit_content, optimize_keywords, validate_schema OU delegar para kernel/seo_orchestrator |
| kernel/seo_orchestrator.py | Existe mas **não é um agente** (não herda BaseAgent); chamado diretamente | Funcionalidade SEO existe mas fora do padrão de agentes | Criar wrapper agent em agents/content/seo_content_suite.py que delega para SEOOrchestrator |
| agents/governance.py | ConstitutionAgent + SurgeonAgent **ainda ativos** | Duplicação com WardenAgent (mesmo papel: validação/guarda) | Decidir: manter Constitution+Surgeon OU migrar para Warden como guardião único |

---

## 🔌 DEPENDÊNCIAS CRÍTICAS VERIFICADAS
| Módulo Kernel | Usado por quais agentes? | Status Integração |
|---------------|--------------------------|-------------------|
| provider_router.py | **Todos agentes BaseAgent** (32 em agents/ + LateralAgent em kernel) via BaseAgent._call_llm → llm_client.call_llm | ✅ Funcional |
| guards.py | **Nenhum agente usa diretamente** (NVIDIA_Guardrails não é chamado em BaseAgent.execute) | ❌ Não integrado |
| sandbox.py | **Nenhum agente usa** (NemoClawSandbox não é instanciado por agentes) | ❌ Não integrado |
| scaler.py | **Nenhum agente usa** (CuOptResourceScaler não é referenciado) | ❌ Não integrado |
| anti_entropy.py | Apenas WardenAgent (pre_execution_check, post_commit_audit) | ⚠️ Parcial — só no Warden |

---

## 🗑️ AGENTES ANTIGOS AINDA NO DISCO (DEVEM SER REMOVIDOS?)
| Arquivo | Classe | Motivo para manter ou deletar |
|---------|--------|-------------------------------|
| agents/scout_agent.py | ScoutAgent | **MANTER** — usado no orchestrator; briefing extraction |
| agents/briefing_agent.py | BriefingAgent | **MANTER** — usado no orchestrator |
| agents/polymath_agent.py | PolymathAgent | **MANTER** — usado no orchestrator; análise profunda |
| agents/strategy_agent.py | StrategyAgent | **MANTER** — usado no orchestrator (the_architect) |
| agents/director_agent.py | DirectorAgent | **MANTER** — usado no orchestrator; approve_plan |
| agents/governance.py | ConstitutionAgent, SurgeonAgent | **REVISAR** — duplicam papel do WardenAgent; se Warden for guardião único, deletar |
| agents/wordsmiths_agent.py | WordsmithsAgent | **MANTER** — usado no orchestrator; copywriting |
| agents/senior_dev_agent.py | SeniorDevAgent | **MANTER** — usado no orchestrator; dev geral |
| agents/voice_agent.py | VoiceAgent | **MANTER** — usado no orchestrator |
| agents/dual_output_agent.py | DualOutputAgent | **MANTER** — usado no orchestrator (the_producer) |
| agents/surgeon_agent.py | SurgeonAgent | **REVISAR** — duplicado em governance.py |
| agents/quality_agent.py | QualityAgent | **MANTER** — usado no orchestrator (the_inspector) |
| agents/optimizer_agent.py | OptimizerAgent | **MANTER** — usado no orchestrator (the_scaler) |
| agents/design_agent.py | DesignAgent | **MANTER** — usado no orchestrator (the_empath) |
| agents/ranker_agent.py | RankerAgent | **MANTER** — usado no orchestrator (the_ranker/seo) |
| agents/lateral_agent.py | LateralAgent | **MANTER** — usado no orchestrator; kernel/lateral_agent.py tbm existe |
| agents/concierge_agent.py | ConciergeAgent | **MANTER** — usado no orchestrator |
| agents/master_key_agent.py | MasterKeyAgent | **MANTER** — usado no orchestrator |
| agents/zoiao_agent.py | ZoiaoAgent | **MANTER** — usado no orchestrator |
| agents/omni_aa_agent.py | OmniAaAgent | **MANTER** — usado no orchestrator |
| agents/minimalist_agent.py | MinimalistAgent | **MANTER** — usado no orchestrator |
| agents/darwin_agent.py | DarwinAgent | **MANTER** — usado no orchestrator |
| agents/gossip_agent.py | GossipAgent | **MANTER** — usado no orchestrator |
| agents/chronic_agent.py | ChronicAgent | **MANTER** — usado no orchestrator |
| agents/inner_spark_agent.py | InnerSparkAgent | **MANTER** — usado no orchestrator |
| agents/prompt_architect_agent.py | PromptArchitectAgent | **MANTER** — usado no orchestrator |
| agents/planner_alpha_agent.py | PlannerAlphaAgent | **MANTER** — usado no orchestrator |
| agents/planner_beta_agent.py | PlannerBetaAgent | **MANTER** — usado no orchestrator |
| agents/senior_dev_core_agent.py | SeniorDevCoreAgent | **MANTER** — usado no orchestrator |
| agents/senior_dev_ops_agent.py | SeniorDevOpsAgent | **MANTER** — usado no orchestrator |
| agents/senior_dev_ui_agent.py | SeniorDevUIAgent | **MANTER** — usado no orchestrator |
| agents/voice_agent.py | VoiceAgent | **MANTER** — usado no orchestrator |

> **Total: 32 agentes em agents/ + 4 em kernel/ (Growth, Creative, Research, Council) = 36 agentes ativos**
> **Plano de redução 40 → 26+3 NÃO EXECUTADO** — nenhum arquivo foi deletado

---

## 🎯 PRÓXIMO PASSO RECOMENDADO
**Ação 1 (Crítica):** Implementar `kernel/autonomy/core/agent_loop.py` com métodos `_cycle()`, `_perceive()`, `_act()`, `_reflect()`, `_escalate()` — hoje é arquivo vazio.

**Ação 2 (Crítica):** Refatorar `kernel/geo_guru/agents/*.py` para injetar `ProviderRouter`, `NVIDIA_Guardrails`, `NemoClawSandbox` via construtor — hoje rodam aiohttp/regex direto, sem quota, sem validação, sem sandbox.

**Ação 3 (Alta):** Criar `agents/content/seo_content_suite.py` herdando `BaseAgent` com métodos `audit_content()`, `optimize_keywords()`, `validate_schema()` que delegam para `kernel/seo_orchestrator.SEOOrchestrator`.

**Ação 4 (Alta):** Registrar `WardenAgent` em `kernel/orchestrator.py` e adicionar hook de `pre_execution_check()` no ciclo de inicialização.

**Ação 5 (Média):** Decidir destino de `agents/governance.py` (ConstitutionAgent + SurgeonAgent) vs `WardenAgent` — manter ambos gera duplicação de lógica de guarda.

**Ação 6 (Média):** Integrar `guards.py` no `BaseAgent.execute()` (validar input/output via `NVIDIA_Guardrails`) e `sandbox.py` para agentes que executam código (SeniorDev, Surgeon, OmniAA).

**Ação 7 (Baixa):** Se plano de redução 40→26 for real, deletar ~10 agentes obsoletos (ex: gossip, chronic, inner_spark, minimalist, darwin, zoiao, omni_aa, senior_dev_ui, senior_dev_ops, senior_dev_core — consolidar em SeniorDevAgent único).