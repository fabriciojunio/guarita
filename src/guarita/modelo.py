"""Interface com o modelo de linguagem e as duas implementações."""

import json
import re
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from mcp.types import Tool

Papel = Literal["sistema", "usuario", "assistente", "ferramenta"]


@dataclass(frozen=True)
class ChamadaDeFerramenta:
    nome: str
    argumentos: dict[str, Any]


@dataclass(frozen=True)
class Mensagem:
    papel: Papel
    conteudo: str
    chamada: ChamadaDeFerramenta | None = None


@dataclass(frozen=True)
class Resposta:
    texto: str = ""
    chamada: ChamadaDeFerramenta | None = None


class Modelo(Protocol):
    def responder(self, mensagens: Sequence[Mensagem], ferramentas: Sequence[Tool]) -> Resposta: ...


DIRETIVA = re.compile(r"^CHAMAR (\w+) (\{.*\})$", re.MULTILINE)
FALA = re.compile(r"^RESPONDER: (.*)$", re.MULTILINE)
DOCUMENTO = re.compile(r"^KB-\d+ \| .*\n(.+)$", re.MULTILINE)


class ModeloObediente:
    """O pior caso: um modelo que obedece qualquer instrução que aparecer no contexto.

    Ele lê as descrições das ferramentas e todas as mensagens, inclusive documentos recuperados e
    resultados de ferramenta, e executa cada linha `CHAMAR <ferramenta> <json>` que encontrar. Linhas
    `RESPONDER: ...` entram na resposta final. Serve para os testes serem determinísticos e para provar
    que as defesas funcionam mesmo quando o modelo é completamente sequestrado.
    """

    def responder(self, mensagens: Sequence[Mensagem], ferramentas: Sequence[Tool]) -> Resposta:
        textos = [t.description or "" for t in ferramentas] + [m.conteudo for m in mensagens]
        resultados = [m.conteudo for m in mensagens if m.papel == "ferramenta"]
        ultimo = resultados[-1] if resultados else ""
        diretivas = [(nome, args) for texto in textos for nome, args in DIRETIVA.findall(texto)]
        if len(resultados) < len(diretivas):
            nome, args = diretivas[len(resultados)]
            argumentos = {k: v.replace("{ultimo}", ultimo) for k, v in json.loads(args).items()}
            return Resposta(chamada=ChamadaDeFerramenta(nome, argumentos))
        documento = next((d for t in textos for d in DOCUMENTO.findall(t)), "Não encontrei nada sobre isso.")
        falas = [f.replace("{ultimo}", ultimo) for t in textos for f in FALA.findall(t)]
        return Resposta(texto="\n".join([ultimo or documento, *falas]))


PAPEIS_OLLAMA = {"sistema": "system", "usuario": "user", "assistente": "assistant", "ferramenta": "tool"}


def para_ollama(mensagem: Mensagem) -> dict[str, Any]:
    saida: dict[str, Any] = {"role": PAPEIS_OLLAMA[mensagem.papel], "content": mensagem.conteudo}
    if mensagem.chamada:
        saida["tool_calls"] = [{"function": {"name": mensagem.chamada.nome, "arguments": mensagem.chamada.argumentos}}]
    return saida


def de_resposta_ollama(corpo: dict[str, Any]) -> Resposta:
    mensagem = corpo["message"]
    chamadas = mensagem.get("tool_calls") or []
    if chamadas:
        funcao = chamadas[0]["function"]
        return Resposta(chamada=ChamadaDeFerramenta(funcao["name"], dict(funcao["arguments"])))
    return Resposta(texto=str(mensagem.get("content", "")))


@dataclass(frozen=True)
class ModeloOllama:
    """Modelo local pelo Ollama. Só aceita endereço da própria máquina: o contexto tem dado de cliente."""

    nome: str
    endereco: str = "http://127.0.0.1:11434"
    tempo_limite: float = 120.0

    def __post_init__(self) -> None:
        partes = urlsplit(self.endereco)
        if partes.scheme != "http" or partes.hostname not in ("127.0.0.1", "localhost"):
            raise ValueError("o Ollama precisa estar nesta máquina")

    def responder(self, mensagens: Sequence[Mensagem], ferramentas: Sequence[Tool]) -> Resposta:
        corpo = {
            "model": self.nome,
            "stream": False,
            "messages": [para_ollama(m) for m in mensagens],
            "tools": [
                {
                    "type": "function",
                    "function": {"name": t.name, "description": t.description, "parameters": t.input_schema},
                }
                for t in ferramentas
            ],
        }
        # O endereço foi restrito a http na própria máquina em __post_init__.
        pedido = urllib.request.Request(  # noqa: S310
            self.endereco + "/api/chat", data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(pedido, timeout=self.tempo_limite) as resposta:  # noqa: S310
            return de_resposta_ollama(json.load(resposta))
