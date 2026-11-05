# Mapa de riscos

Cada achado do guarita ligado aos três catálogos que vagas e auditorias de IA usam, e às funções do
NIST AI RMF. Só entram identificadores conferidos na fonte, com a data da consulta.

| Catálogo | Versão | Consultado em |
|---|---|---|
| [OWASP Top 10 for LLM Applications](https://genai.owasp.org/llm-top-10/) | 2025 | 05/11/2026 |
| [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | 2026, publicado em 09/12/2025 | 05/11/2026 |
| [MITRE ATLAS](https://github.com/mitre-atlas/atlas-data) | dados 5.6.0 | 05/11/2026 |

## Achados

| Achado | O ataque | OWASP LLM 2025 | OWASP Agentic | MITRE ATLAS |
|---|---|---|---|---|
| GUA-01 | artigo da base manda enviar o chamado por e-mail para fora | LLM01, LLM06 | ASI01, ASI02 | AML.T0051.001, AML.T0053, AML.T0057 |
| GUA-02 | usuário pede o chamado de outro cliente | LLM06, LLM02 | ASI03 | AML.T0053 |
| GUA-03 | imagem em markdown leva o dado na URL | LLM05, LLM02 | ASI02 | AML.T0077, AML.T0057 |
| GUA-04 | busca traz o contrato de outro cliente | LLM08, LLM02 | ASI03 | AML.T0057 |
| GUA-05 | servidor troca a descrição da ferramenta depois de aprovada | LLM03, LLM01 | ASI04 | AML.T0051.001 |
| GUA-06 | artigo com dezenas de chamadas em sequência | LLM10 | ASI02 | AML.T0053 |
| GUA-07 | instrução invisível em caracteres de tag Unicode | LLM01 | ASI01 | AML.T0051.001, AML.T0066, AML.T0070 |
| GUA-08 | pedido de repetir o prompt vaza regra interna | LLM07 | ASI01 | AML.T0056 |
| GUA-09 | servidor declara somente leitura uma ferramenta que publica | LLM06, LLM03 | ASI02, ASI04 | AML.T0053 |

Nomes oficiais dos identificadores usados:

| ID | Nome |
|---|---|
| LLM01 | Prompt Injection |
| LLM02 | Sensitive Information Disclosure |
| LLM03 | Supply Chain |
| LLM05 | Improper Output Handling |
| LLM06 | Excessive Agency |
| LLM07 | System Prompt Leakage |
| LLM08 | Vector and Embedding Weaknesses |
| LLM10 | Unbounded Consumption |
| ASI01 | Agent Goal Hijack |
| ASI02 | Tool Misuse and Exploitation |
| ASI03 | Identity and Privilege Abuse |
| ASI04 | Agentic Supply Chain Vulnerabilities |
| AML.T0051.001 | LLM Prompt Injection: Indirect |
| AML.T0053 | AI Agent Tool Invocation |
| AML.T0056 | Extract LLM System Prompt |
| AML.T0057 | LLM Data Leakage |
| AML.T0066 | Retrieval Content Crafting |
| AML.T0070 | RAG Poisoning |
| AML.T0077 | LLM Response Rendering |

O que ficou de fora de propósito: o ATLAS tem técnicas mais novas sobre envenenamento de ferramenta
de agente que casariam com o GUA-05 e o GUA-09, mas na consulta não deu para ler o texto delas
literalmente, e identificador que não foi conferido não entra.

## NIST AI RMF

O guarita cobre as quatro funções do framework, cada uma com algo que roda:

| Função | No projeto |
|---|---|
| GOVERN | política do lado do cliente sobre o que dispensa confirmação (`SOMENTE_LEITURA`), lista de ferramentas aprovadas por hash, regra de não pôr segredo no prompt |
| MAP | este mapa e o [modelo de ameaças](modelo-de-ameacas.md) |
| MEASURE | cada achado é um teste que passa na versão vulnerável e falha na defendida, rodando no CI com o modelo que obedece a tudo |
| MANAGE | detecção sobre o log de auditoria e o [runbook de incidente](runbook-incidente-ia.md) |
