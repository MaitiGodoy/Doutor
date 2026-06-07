# 🧠 MEMORY.md — Contexto Ambiental e Lições Aprendidas

## Estrutura do Projeto
```
/var/www/maiti-godoy-portal/doutor/     → Doutor v5.0 production (VPS)
/var/www/gericfast/doutor/               → Doutor v5.0 gericfast
/opt/gericfast-cic/                      → CIC microservice
C:\Users\User\.gemini\antigravity-ide\scratch\doutor\  → Local dev + Doutor 6.0
```

## Convenções de Código
- Python 3.11+ com type hints obrigatórios
- FastAPI para servidores HTTP
- SQLite para state local, PostgreSQL para persistência
- Docker Compose v3.8+ para orquestração
- Nginx como reverse proxy com SSL Let's Encrypt
- Senha admin unificada: Sh48151623 (todos os projetos)

## Restrições de Governança
1. **LGPD** — Nenhum dado pessoal sem criptografia
2. **Rate Limits** — Respeitar cotas dos providers (429 = backoff)
3. **Token Safety** — Não expor chaves de API em logs ou outputs
4. **Audit Trail** — Toda ação deve ser logada

## Lições Aprendidas (Histórico)
1. Hermes CLI one-shot quebrou porque .env estava vazio e docker-compose sobrescrevia a key. Fix: usar ~/.hermes/.env + remover override.
2. Windows + create_subprocess_shell = SyntaxError. Fix: usar create_subprocess_exec + base64 para payload.
3. Full pipeline com 30+ agents paralelos excede rate limits free-tier. Fix: sequenciar chamadas com backoff exponencial.
4. Orchestrator com path relativo quebra em subprocess. Fix: sempre usar Path(__file__).resolve().parent.
5. VPS usa arquitetura monolithic v4.7 (mcp_server.py 43KB). Local usa modular v5.0. Ao patchar VPS, aplicar cirurgicamente.
6. Hermes Agent roda em Docker (nousresearch/hermes-agent). Porta 8642. Não expor publicamente — only localhost + nginx proxy.

## Tasks Agendadas
- [cron] 0 2 * * * → Auditoria de segurança full (todos repositórios)
- [cron] 0 9 * * 1 → Pesquisa de tendências de tecnologia (Agente Maconheiro)
- [cron] @every 1h → Verificar fila de tarefas e distribuir entre agentes
