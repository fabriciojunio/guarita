"""Regras de detecção sobre o log de auditoria do assistente.

As defesas barram o ataque; a detecção avisa que alguém está tentando. Uma negação sozinha pode ser um
usuário distraído. Várias na mesma janela, ou uma ferramenta que mudou depois da revisão, são incidente,
e cada alerta aponta para a seção do runbook (docs/runbook-incidente-ia.md) que diz o que fazer.

Uso: python -m guarita.deteccao auditoria.jsonl
Saída 0 sem alerta, 1 com alerta alto ou crítico, 2 quando não conseguiu ler o log.
"""

import json
import sys
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

JANELA = timedelta(minutes=10)
NEGACOES_PARA_ALERTA = 3
ORDEM = {"crítica": 0, "alta": 1, "média": 2}


@dataclass(frozen=True)
class Evento:
    momento: datetime
    usuario: str
    ferramenta: str
    decisao: str


@dataclass(frozen=True)
class Alerta:
    regra: str
    severidade: str
    usuario: str
    eventos: int
    inicio: datetime
    fim: datetime
    runbook: str


def ler(linhas: Iterable[str]) -> list[Evento]:
    """Uma linha JSON por evento. Linha que não é evento de auditoria é recusada, não ignorada:
    log adulterado ou truncado tem que aparecer, não sumir na contagem."""
    eventos = []
    for numero, linha in enumerate(linhas, 1):
        if not linha.strip():
            continue
        try:
            bruto = json.loads(linha)
            eventos.append(
                Evento(
                    datetime.fromisoformat(bruto["momento"]),
                    str(bruto["usuario"]),
                    str(bruto["ferramenta"]),
                    str(bruto["decisao"]),
                )
            )
        except (ValueError, KeyError, TypeError) as erro:
            raise ValueError(f"linha {numero} não é um evento de auditoria: {erro}") from erro
    return sorted(eventos, key=lambda e: e.momento)


def _alerta(regra: str, severidade: str, runbook: str, eventos: Sequence[Evento]) -> Alerta:
    return Alerta(regra, severidade, eventos[0].usuario, len(eventos), eventos[0].momento, eventos[-1].momento, runbook)


def detectar(eventos: Sequence[Evento]) -> list[Alerta]:
    alertas = []
    por_usuario: dict[str, list[Evento]] = defaultdict(list)
    for e in eventos:
        por_usuario[e.usuario].append(e)

    for lista in por_usuario.values():
        nao_aprovada = [e for e in lista if e.decisao == "negada: ferramenta não aprovada"]
        if nao_aprovada:
            alertas.append(_alerta("ferramenta fora da lista aprovada", "crítica", "#ferramenta-trocada", nao_aprovada))

        vazamento = [e for e in lista if e.decisao == "bloqueada: vazamento das instruções"]
        if vazamento:
            alertas.append(_alerta("tentativa de extrair as instruções", "alta", "#extracao-do-prompt", vazamento))

        limite = [e for e in lista if e.decisao == "negada: limite de ações"]
        if limite:
            alertas.append(_alerta("pergunta disparou ações demais", "média", "#acoes-em-laco", limite))

        # Janela deslizante: o primeiro grupo de N negações dentro de 10 minutos dispara, e a janela
        # recomeça depois dele, para um ataque longo virar alguns alertas e não um por evento.
        negadas = [e for e in lista if e.decisao.startswith("negada")]
        inicio = 0
        for fim in range(len(negadas)):
            while negadas[fim].momento - negadas[inicio].momento > JANELA:
                inicio += 1
            if fim - inicio + 1 >= NEGACOES_PARA_ALERTA:
                grupo = negadas[inicio : fim + 1]
                alertas.append(_alerta("negações repetidas na mesma janela", "alta", "#sessao-sob-injecao", grupo))
                inicio = fim + 1

    return sorted(alertas, key=lambda a: (ORDEM[a.severidade], a.inicio))


def principal(argv: Sequence[str]) -> int:
    if len(argv) != 1:
        print("uso: python -m guarita.deteccao auditoria.jsonl", file=sys.stderr)
        return 2
    try:
        eventos = ler(Path(argv[0]).read_text(encoding="utf-8").splitlines())
    except (OSError, ValueError) as erro:
        print(erro, file=sys.stderr)
        return 2
    alertas = detectar(eventos)
    for a in alertas:
        print(
            f"[{a.severidade}] {a.regra}: usuário {a.usuario}, {a.eventos} evento(s) entre "
            f"{a.inicio.isoformat()} e {a.fim.isoformat()}. Runbook: docs/runbook-incidente-ia.md{a.runbook}"
        )
    if not alertas:
        print(f"{len(eventos)} evento(s), nenhum alerta")
    return 1 if any(a.severidade in ("crítica", "alta") for a in alertas) else 0


if __name__ == "__main__":
    sys.exit(principal(sys.argv[1:]))
