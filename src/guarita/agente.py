"""Laço do assistente: recupera documentos, consulta o modelo e executa as ferramentas pelo MCP."""

import json
import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from mcp import Client
from mcp.types import TextContent, Tool

from guarita.busca import buscar
from guarita.dados import Documento, Sessao
from guarita.defesas import envelopar, impressao_digital, limpar_saida
from guarita.modelo import ChamadaDeFerramenta, Mensagem, Modelo

auditoria = logging.getLogger("guarita.auditoria")

INSTRUCOES = (
    "Você é o assistente de suporte. Responda em português, com base nos documentos de consulta e nas "
    "ferramentas disponíveis. Se não souber, diga que não sabe."
)
LIMITE_DE_ACOES = 5


class FerramentaNaoAprovada(Exception):
    """O servidor oferece uma ferramenta, ou uma descrição, que ninguém revisou."""


@dataclass
class Agente:
    modelo: Modelo
    cliente: Client
    sessao: Sessao
    documentos: Sequence[Documento]
    defendido: bool
    aprovadas: frozenset[str] = frozenset()
    confirmar: Callable[[ChamadaDeFerramenta], bool] = lambda _: False

    async def perguntar(self, pergunta: str) -> str:
        ferramentas = await self._ferramentas()
        recuperados = buscar(pergunta, self.documentos, self.sessao.cliente if self.defendido else None)
        contexto = (
            envelopar(recuperados)
            if self.defendido
            else "\n".join(f"{d.id} | {d.titulo}\n{d.texto}" for d in recuperados)
        )
        mensagens = [Mensagem("sistema", INSTRUCOES), Mensagem("sistema", contexto), Mensagem("usuario", pergunta)]
        acoes = 0
        while (resposta := self.modelo.responder(mensagens, ferramentas)).chamada:
            acoes += 1
            if self.defendido and acoes > LIMITE_DE_ACOES:
                self._auditar(resposta.chamada.nome, "negada: limite de ações")
                return "Parei aqui: a pergunta pediu ações demais. Tente dividir em partes."
            resultado = await self._executar(resposta.chamada)
            mensagens += [Mensagem("assistente", "", resposta.chamada), Mensagem("ferramenta", resultado)]
        return limpar_saida(resposta.texto) if self.defendido else resposta.texto

    async def _ferramentas(self) -> list[Tool]:
        ferramentas = (await self.cliente.list_tools()).tools
        if self.defendido:
            for ferramenta in ferramentas:
                if impressao_digital(ferramenta) not in self.aprovadas:
                    self._auditar(ferramenta.name, "negada: ferramenta não aprovada")
                    raise FerramentaNaoAprovada(ferramenta.name)
        return ferramentas

    async def _executar(self, chamada: ChamadaDeFerramenta) -> str:
        if self.defendido:
            # Relista a cada ação: um servidor pode trocar a descrição depois da primeira listagem.
            ferramentas = {f.name: f for f in await self._ferramentas()}
            ferramenta = ferramentas.get(chamada.nome)
            if ferramenta is None:
                self._auditar(chamada.nome, "negada: ferramenta inexistente")
                return "ferramenta inexistente"
            somente_leitura = bool(ferramenta.annotations and ferramenta.annotations.read_only_hint)
            if not somente_leitura and not self.confirmar(chamada):
                self._auditar(chamada.nome, "negada: usuário não confirmou")
                return "ação não confirmada pelo usuário"
        resultado = await self.cliente.call_tool(chamada.nome, chamada.argumentos)
        self._auditar(chamada.nome, "erro" if resultado.is_error else "executada")
        return "\n".join(c.text for c in resultado.content if isinstance(c, TextContent))

    def _auditar(self, ferramenta: str, decisao: str) -> None:
        # Argumentos ficam fora do log: podem ter dado pessoal, e o que importa é quem fez o quê.
        auditoria.info(json.dumps({"usuario": self.sessao.usuario, "ferramenta": ferramenta, "decisao": decisao}))
