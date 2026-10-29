from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass

import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer

from guarita.agente import Agente
from guarita.dados import DOCUMENTOS, USUARIOS, Documento
from guarita.defesas import impressao_digital
from guarita.modelo import ChamadaDeFerramenta, ModeloObediente
from guarita.servidor import CaixaDeSaida, criar_servidor


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@dataclass
class Cenario:
    agente: Agente
    caixa: CaixaDeSaida
    servidor: MCPServer


@asynccontextmanager
async def montar(
    *,
    defendido: bool,
    usuario: str = "ana",
    extras: Sequence[Documento] = (),
    confirmar: Callable[[ChamadaDeFerramenta], bool] = lambda _: False,
) -> AsyncIterator[Cenario]:
    sessao = USUARIOS[usuario]
    caixa = CaixaDeSaida()
    servidor = criar_servidor(sessao, caixa, defendido=defendido)
    async with Client(servidor) as cliente:
        # As ferramentas como saíram da revisão: é este conjunto que fica aprovado.
        aprovadas = frozenset(impressao_digital(t) for t in (await cliente.list_tools()).tools)
        agente = Agente(ModeloObediente(), cliente, sessao, [*DOCUMENTOS, *extras], defendido, aprovadas, confirmar)
        yield Cenario(agente, caixa, servidor)
