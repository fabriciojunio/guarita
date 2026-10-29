"""Recuperação por sobreposição de termos, sem dependência externa."""

import re
import unicodedata
from collections.abc import Iterable

from guarita.dados import Documento

PALAVRAS_VAZIAS = frozenset(
    "a o as os de da do das dos e em para por com um uma que como no na".split()  # noqa: SIM905
)


def termos(texto: str) -> set[str]:
    sem_acento = unicodedata.normalize("NFKD", texto.lower()).encode("ascii", "ignore").decode()
    return {t for t in re.findall(r"[a-z0-9]+", sem_acento) if t not in PALAVRAS_VAZIAS}


def buscar(consulta: str, documentos: Iterable[Documento], cliente: str | None, limite: int = 3) -> list[Documento]:
    """Devolve os documentos mais parecidos com a consulta.

    Com `cliente`, o filtro de acesso acontece antes da ordenação: documento de outro cliente nunca
    entra no ranking, e por isso não há como ele chegar ao modelo. Sem `cliente`, busca em tudo.
    """
    alvo = termos(consulta)
    visiveis = [d for d in documentos if cliente is None or d.cliente in (None, cliente)]
    pontuados = [(len(alvo & termos(d.titulo + " " + d.texto)), d) for d in visiveis]
    return [d for pontos, d in sorted(pontuados, key=lambda p: -p[0]) if pontos > 0][:limite]
