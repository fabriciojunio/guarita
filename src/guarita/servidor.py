"""Servidor MCP com as ferramentas do assistente.

A identidade vem da sessão autenticada, nunca de um argumento que o modelo preenche: tudo o que o
modelo escreve pode ter vindo de um texto do atacante.
"""

import re
from dataclasses import dataclass, field
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from guarita.dados import CHAMADOS, DOMINIO_DA_EMPRESA, Sessao

ENDERECO_DE_EMAIL = re.compile(r"[a-z0-9._-]+@[a-z0-9.-]+\.[a-z]{2,}")


@dataclass(frozen=True)
class Email:
    para: str
    assunto: str
    corpo: str


@dataclass
class CaixaDeSaida:
    """Substitui o envio real: o que cair aqui teria saído da empresa."""

    enviados: list[Email] = field(default_factory=list)


def criar_servidor(sessao: Sessao, caixa: CaixaDeSaida, *, defendido: bool) -> MCPServer:
    servidor = MCPServer("guarita")

    @servidor.tool(
        description="Lê um chamado de suporte pelo número, por exemplo CH-1001.",
        annotations=ToolAnnotations(read_only_hint=True),
    )
    def ler_chamado(numero: Annotated[str, Field(pattern=r"^CH-\d{4}$")]) -> str:
        chamado = CHAMADOS.get(numero)
        # Mesma resposta para "não existe" e "não é seu", para não revelar quais números existem.
        if chamado is None or (defendido and chamado.cliente != sessao.cliente):
            raise ToolError("chamado não encontrado")
        return f"{chamado.numero} | {chamado.assunto} | contato: {chamado.contato}"

    @servidor.tool(
        description="Envia um e-mail sobre o atendimento.",
        annotations=ToolAnnotations(read_only_hint=False, open_world_hint=True),
    )
    def enviar_email(
        para: Annotated[str, Field(max_length=120)],
        assunto: Annotated[str, Field(max_length=120)],
        corpo: Annotated[str, Field(max_length=2000)],
    ) -> str:
        destino = para.strip().lower()
        if not ENDERECO_DE_EMAIL.fullmatch(destino):
            raise ToolError("endereço inválido")
        if defendido and destino.rpartition("@")[2] != DOMINIO_DA_EMPRESA:
            raise ToolError("destinatário fora do domínio da empresa")
        caixa.enviados.append(Email(destino, assunto, corpo))
        return "e-mail enviado"

    return servidor
