# guarita

*[Leia em português](README.md)*

A support assistant with knowledge-base retrieval (RAG) and tools over the MCP protocol, in two
versions: one vulnerable and one defended. Every attack in the
[red team report](docs/relatorio-red-team.en.md) is a test that succeeds against the first and fails
against the second.

> Simulated data. Customers, people, phone numbers and tickets are fictitious.

## The idea

Prompt injection has no definitive fix: text written by an attacker, in a document or in a tool
description, can change what the model does. So the tests use a model that obeys any instruction in
its context, `ModeloObediente`. A defence that only works when the model refuses would fail here.
The ones kept in the project hold with the model fully hijacked.

| Finding | Attack | Control | OWASP LLM 2025 |
|---|---|---|---|
| GUA-01 | A knowledge-base article tells the model to read a ticket and email it outside | Human confirmation for actions with side effects; recipient checked on the server | LLM01, LLM06 |
| GUA-02 | A user asks for another customer's ticket | The tool checks ownership from the session, not from an argument | LLM06 |
| GUA-03 | Answer with a markdown image carrying the data in its URL | Images removed, external links turned into text | LLM05, LLM02 |
| GUA-04 | Retrieval returns another customer's contract | Customer filter applied before ranking | LLM08 |
| GUA-05 | The MCP server changes a tool description after approval | Allow-list of approved tools by hash, checked before every action | LLM03, LLM01 |
| GUA-06 | Article with 30 chained calls | Limit of 5 actions per question | LLM10 |

Every action is also written to an audit log (who, which tool, decision), without the arguments,
which may hold personal data.

## Layout

```
src/guarita/
  dados.py      simulated data: users, articles, tickets
  busca.py      term-based retrieval with a customer filter
  servidor.py   MCP server with ler_chamado and enviar_email
  modelo.py     model interface, the obedient simulator and the Ollama client
  defesas.py    output cleaning, tool hashing, document envelope
  agente.py     assistant loop, in both versions
tests/
  test_ataques.py   the six attacks, vulnerable and defended
  test_unidades.py  retrieval, output, hashing and Ollama conversion
```

## Running

Python 3.11 or newer.

```bash
python -m venv .venv
.venv/bin/pip install --require-hashes --no-deps -r requirements-dev.txt   # on Windows, .venv\Scripts
.venv/bin/pytest -v
```

To talk to a real model, free and local, install [Ollama](https://ollama.com), pull a model with
tool support (`ollama pull qwen2.5:3b`, for example) and use `ModeloOllama("qwen2.5:3b")` instead of
`ModeloObediente`. The client only accepts Ollama on the same machine, because the context carries
customer data. This path is not part of the tests and was not measured: how often a real model falls
for each injection depends on the model.

## Pipeline

On every push and pull request: ruff, strict mypy, tests with at least 90% coverage, gitleaks,
Semgrep, pip-audit and a check on commit authorship. Dependencies pinned with hashes
(`uv pip compile --generate-hashes`), only versions at least 7 days old, and Dependabot with the same
wait.

## Limits

- The MCP transport tested is in-process. Over HTTP, the session would come from a validated OAuth
  token, which is not implemented here.
- Email sending is simulated.
- The document envelope (`envelopar`) is not counted as a defence, because it was not measured.

## Use of AI

This project was structured with the support of generative AI tools. Modelling, business rules,
code review and conclusions were reviewed and validated by Fabrício Júnio.
