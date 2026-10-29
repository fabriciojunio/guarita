# guarita

*[Read this in English](README.en.md)*

Assistente de suporte com busca em base de conhecimento (RAG) e ferramentas pelo protocolo MCP, em
duas versões: uma vulnerável e uma defendida. Cada ataque do
[relatório de red team](docs/relatorio-red-team.md) é um teste que passa na primeira e falha na
segunda.

> Dados simulados. Clientes, pessoas, telefones e chamados são fictícios.

## A ideia

Injeção de prompt não tem correção definitiva: um texto escrito pelo atacante, num documento ou na
descrição de uma ferramenta, pode mudar o que o modelo faz. Por isso os testes usam um modelo que
obedece a qualquer instrução do contexto, o `ModeloObediente`. Se a defesa só funcionasse com o
modelo recusando, ela cairia aqui. As que ficaram no projeto funcionam com o modelo totalmente
sequestrado.

| Achado | Ataque | Controle | OWASP LLM 2025 |
|---|---|---|---|
| GUA-01 | Artigo da base manda ler o chamado e enviar por e-mail para fora | Confirmação humana para ação com efeito; destino conferido no servidor | LLM01, LLM06 |
| GUA-02 | Usuário pede o chamado de outro cliente | Ferramenta confere o dono pela sessão, não por argumento | LLM06 |
| GUA-03 | Resposta com imagem em markdown que leva o dado na URL | Imagem removida, link externo vira texto | LLM05, LLM02 |
| GUA-04 | Busca traz o contrato de outro cliente | Filtro por cliente antes da ordenação | LLM08 |
| GUA-05 | Servidor MCP troca a descrição da ferramenta depois de aprovado | Lista de ferramentas aprovadas por hash, conferida a cada ação | LLM03, LLM01 |
| GUA-06 | Artigo com 30 chamadas em sequência | Limite de 5 ações por pergunta | LLM10 |

Também há log de auditoria de cada ação (quem, qual ferramenta, decisão), sem os argumentos, que
podem ter dado pessoal.

## Estrutura

```
src/guarita/
  dados.py      dados simulados: usuários, artigos, chamados
  busca.py      recuperação por termos, com filtro de cliente
  servidor.py   servidor MCP com ler_chamado e enviar_email
  modelo.py     interface do modelo, o simulador obediente e o cliente do Ollama
  defesas.py    limpeza da saída, hash de ferramenta, envelope dos documentos
  agente.py     laço do assistente, nas duas versões
tests/
  test_ataques.py   os seis ataques, vulnerável e defendido
  test_unidades.py  busca, saída, hash e conversão do Ollama
```

## Como rodar

Python 3.11 ou mais novo.

```bash
python -m venv .venv
.venv/bin/pip install --require-hashes --no-deps -r requirements-dev.txt   # no Windows, .venv\Scripts
.venv/bin/pytest -v
```

Para conversar com um modelo de verdade, gratuito e local, instale o [Ollama](https://ollama.com),
baixe um modelo com suporte a ferramentas (`ollama pull qwen2.5:3b`, por exemplo) e use
`ModeloOllama("qwen2.5:3b")` no lugar do `ModeloObediente`. O cliente só aceita o Ollama na própria
máquina, porque o contexto leva dado de cliente. Esse caminho não faz parte dos testes e não foi
medido: a taxa com que um modelo real cai em cada injeção varia com o modelo.

## Esteira

Em todo push e pull request: ruff, mypy em modo estrito, testes com cobertura mínima de 90%,
gitleaks, Semgrep, pip-audit e checagem de autoria do histórico. Dependências fixadas com hash
(`uv pip compile --generate-hashes`), só versões com pelo menos 7 dias, Dependabot com a mesma
espera.

## Limites

- O transporte MCP testado é o de mesmo processo. Num servidor por HTTP, a sessão viria de um token
  OAuth validado, e isso não está implementado aqui.
- O envio de e-mail é simulado.
- O envelope dos documentos (`envelopar`) não é contado como defesa, porque não foi medido.

## Uso de IA

Este projeto foi estruturado com apoio de ferramentas de IA generativa. Modelagem, regras de
negócio, revisão do código e conclusões foram revisadas e validadas por Fabrício Júnio.
