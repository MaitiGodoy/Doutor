import asyncio
from typing import Dict, List

class GEO_EntityWriter:
    def __init__(self):
        self.tone_guidelines = {
            "technical": "Denso em entidades, resposta direta, sem ambiguidade",
            "marketing": "Persuasivo mas factual, com citações verificáveis",
            "educational": "Explicativo, com exemplos concretos e fontes"
        }
    
    async def generate(self, plan: Dict) -> str:
        """Gera conteúdo entity-dense otimizado para LLMs"""
        plan_type = plan.get("type", "alpha")
        
        if plan_type == "alpha":
            return await self._generate_faq(plan)
        elif plan_type == "beta":
            return await self._generate_technical_doc(plan)
        elif plan_type == "gamma":
            return await self._generate_listicle(plan)
        else:
            return await self._generate_article(plan)
    
    async def _generate_faq(self, plan: Dict) -> str:
        queries = plan.get("target_queries", [])
        content = "# Perguntas Frequentes (Otimizado para IA)\n\n"
        
        for i, query in enumerate(queries[:5], 1):
            content += f"## {query}\n"
            content += f"**Resposta direta:** [Inserir resposta factual em 2-3 frases]\n"
            content += f"**Detalhes:** [Expandir com dados estruturados e citações]\n"
            content += f"**Fonte:** [URL verificável]\n\n"
        
        return content
    
    async def _generate_technical_doc(self, plan: Dict) -> str:
        return """# Documentação Técnica

## Visão Geral
[Descrição factual e densa em entidades]

## Especificações
- **Entidade Principal:** [Nome]
- **Relações:** [Lista de relações entidade-atributo]
- **Fontes:** [Referências primárias]

## Implementação
[Código ou protocolo técnico]

## Referências
[Links para documentação open-source]
"""
    
    async def _generate_listicle(self, plan: Dict) -> str:
        return """# Lista Numerada (Dados Estruturados)

1. **Item 1:** [Fato verificável]
   - Detalhes: [Dados estruturados]
   - Fonte: [URL]

2. **Item 2:** [Fato verificável]
   - Detalhes: [Dados estruturados]
   - Fonte: [URL]

[Continuar para 5-10 itens]
"""
    
    async def _generate_article(self, plan: Dict) -> str:
        return """# Artigo Jornalístico

**Lead:** [Resumo factual em 1-2 frases]

**Corpo:**
[Parágrafos curtos com citações diretas]
[Fontes atribuídas claramente]

**Conclusão:**
[Resumo factual sem especulação]

**Fontes:**
- [Lista de referências verificáveis]
"""
    
    async def rewrite(self, content: str, fixes: List[str]) -> str:
        """Reescreve conteúdo aplicando correções do council"""
        rewritten = content
        
        for fix in fixes:
            if "fontes" in fix.lower():
                rewritten += "\n\n**Fontes Adicionais:** [Inserir URLs verificáveis]"
            if "especulativa" in fix.lower():
                # Remove linguagem especulativa (mock)
                rewritten = rewritten.replace("provavelmente", "").replace("talvez", "")
        
        return rewritten