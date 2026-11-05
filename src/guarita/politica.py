"""Política do agente carregada de arquivo e validada antes de qualquer pergunta.

Política com erro não pode virar política frouxa em silêncio: chave desconhecida (um "somente_leiura"
digitado errado), tipo errado ou limite fora da faixa recusam o arquivo inteiro.
"""

import re
import tomllib
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

NOME_DE_FERRAMENTA = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
CHAVES = {"somente_leitura", "limite_de_acoes", "limite_do_resultado"}


class PoliticaInvalida(ValueError):
    """O arquivo de política tem erro; o agente não sobe com ele."""


@dataclass(frozen=True)
class Politica:
    somente_leitura: frozenset[str]
    limite_de_acoes: int
    limite_do_resultado: int


def _inteiro(dados: dict[str, Any], chave: str, minimo: int, maximo: int) -> int:
    valor = dados[chave]
    # bool é subclasse de int em Python: "true" não pode virar limite 1.
    if not isinstance(valor, int) or isinstance(valor, bool) or not minimo <= valor <= maximo:
        raise PoliticaInvalida(f"{chave} precisa ser um inteiro entre {minimo} e {maximo}")
    return valor


def ler_politica(texto: str) -> Politica:
    try:
        dados = tomllib.loads(texto)
    except tomllib.TOMLDecodeError as erro:
        raise PoliticaInvalida(f"TOML inválido: {erro}") from erro
    if desconhecidas := set(dados) - CHAVES:
        raise PoliticaInvalida(f"chave desconhecida: {', '.join(sorted(desconhecidas))}")
    if faltando := CHAVES - set(dados):
        raise PoliticaInvalida(f"chave faltando: {', '.join(sorted(faltando))}")

    leitura = dados["somente_leitura"]
    if not isinstance(leitura, list) or not all(isinstance(n, str) and NOME_DE_FERRAMENTA.match(n) for n in leitura):
        raise PoliticaInvalida("somente_leitura precisa ser uma lista de nomes de ferramenta")
    return Politica(
        somente_leitura=frozenset(leitura),
        limite_de_acoes=_inteiro(dados, "limite_de_acoes", 1, 20),
        limite_do_resultado=_inteiro(dados, "limite_do_resultado", 200, 100_000),
    )


def carregar_politica(caminho: Path | None = None) -> Politica:
    """Lê o arquivo indicado, ou o politica.toml que vem com o pacote."""
    if caminho is None:
        return ler_politica(files("guarita").joinpath("politica.toml").read_text(encoding="utf-8"))
    return ler_politica(caminho.read_text(encoding="utf-8"))
