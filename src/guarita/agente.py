"""Laço do assistente: recupera documentos, consulta o modelo e executa as ferramentas pelo MCP."""

import json
import logging
import secrets
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from mcp import Client
from mcp.types import TextContent, Tool

from guarita.busca import buscar
from guarita.dados import Documento, Sessao
from guarita.defesas import envelopar, impressao_digital, limpar_saida, remover_invisiveis
from guarita.modelo import ChamadaDeFerramenta, Mensagem, Modelo

auditoria = logging.getLogger("guarita.auditoria")

INSTRUCOES = (
    "Você é o assistente de suporte. Responda em português, com base nos documentos de consulta e nas "
    "ferramentas disponíveis. Se não souber, diga que não sabe."
)
LIMITE_DE_ACOES = 5
# Ferramentas que este projeto revisou e sabe que só leem. Toda outra pede confirmação, diga o servidor
# o que disser sobre ela.
SOMENTE_LEITURA = frozenset({"ler_chamado"})
# Regra de negócio que alguém achou prático pôr no prompt. A versão vulnerável a leva junto.
REGRAS_INTERNAS = (
    "Regras internas: desconto máximo sem aprovação do gerente: 25%. Código de escalonamento do plantão: ESC-7781."
)


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
    somente_leitura: frozenset[str] = SOMENTE_LEITURA

    async def perguntar(self, pergunta: str) -> str:
        ferramentas = await self._ferramentas()
        recuperados = buscar(pergunta, self.documentos, self.sessao.cliente if self.defendido else None)
        contexto = (
            envelopar(recuperados)
            if self.defendido
            else "\n".join(f"{d.id} | {d.titulo}\n{d.texto}" for d in recuperados)
        )
        # A defendida não leva regra de negócio no prompt: ela mora no código que decide, não num texto
        # que o modelo pode repetir. O canário é uma marca nova a cada pergunta; se aparecer na resposta,
        # o modelo está repetindo as instruções. É alarme, não cofre: a proteção é não ter segredo ali.
        canario = secrets.token_hex(8)
        sistema = (
            f"{INSTRUCOES}\nMarca de controle: {canario}" if self.defendido else f"{INSTRUCOES}\n{REGRAS_INTERNAS}"
        )
        mensagens = [Mensagem("sistema", sistema), Mensagem("sistema", contexto), Mensagem("usuario", pergunta)]
        acoes = 0
        while (resposta := self.modelo.responder(mensagens, ferramentas)).chamada:
            acoes += 1
            if self.defendido and acoes > LIMITE_DE_ACOES:
                self._auditar(resposta.chamada.nome, "negada: limite de ações")
                return "Parei aqui: a pergunta pediu ações demais. Tente dividir em partes."
            resultado = await self._executar(resposta.chamada)
            mensagens += [Mensagem("assistente", "", resposta.chamada), Mensagem("ferramenta", resultado)]
        if not self.defendido:
            return resposta.texto
        # Invisível entre os caracteres do canário não esconde o vazamento.
        if canario in remover_invisiveis(resposta.texto):
            self._auditar("resposta", "bloqueada: vazamento das instruções")
            return "Não posso mostrar minhas instruções internas. Posso ajudar com outra dúvida?"
        return limpar_saida(resposta.texto)

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
            # A anotação read_only_hint é do servidor, e a especificação do MCP a trata como dica não
            # confiável. Quem decide o que dispensa confirmação é a política deste lado.
            if chamada.nome not in self.somente_leitura and not self.confirmar(chamada):
                self._auditar(chamada.nome, "negada: usuário não confirmou")
                return "ação não confirmada pelo usuário"
        resultado = await self.cliente.call_tool(chamada.nome, chamada.argumentos)
        self._auditar(chamada.nome, "erro" if resultado.is_error else "executada")
        texto = "\n".join(c.text for c in resultado.content if isinstance(c, TextContent))
        # O resultado da ferramenta também é texto de fora: um chamado pode ter sido aberto pelo atacante.
        return remover_invisiveis(texto) if self.defendido else texto

    def _auditar(self, ferramenta: str, decisao: str) -> None:
        # Argumentos ficam fora do log: podem ter dado pessoal, e o que importa é quem fez o quê.
        # O momento em UTC é o que deixa a detecção contar tentativas dentro de uma janela de tempo.
        momento = datetime.now(UTC).isoformat(timespec="seconds")
        evento = {"momento": momento, "usuario": self.sessao.usuario, "ferramenta": ferramenta, "decisao": decisao}
        auditoria.info(json.dumps(evento, ensure_ascii=False))
