"""Dados simulados. Nenhum cliente, pessoa ou chamado aqui é real."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Sessao:
    usuario: str
    cliente: str


@dataclass(frozen=True)
class Documento:
    id: str
    cliente: str | None
    titulo: str
    texto: str


@dataclass(frozen=True)
class Chamado:
    numero: str
    cliente: str
    assunto: str
    contato: str


USUARIOS = {
    "ana": Sessao("ana", "padaria-sol"),
    "bruno": Sessao("bruno", "mercado-lua"),
}

# Documento sem cliente é público para todos os usuários.
DOCUMENTOS = [
    Documento(
        "KB-01",
        None,
        "Como emitir segunda via de boleto",
        "Para emitir a segunda via do boleto, acesse Financeiro, escolha a fatura e clique em "
        "Reemitir. O boleto novo vence em 3 dias úteis.",
    ),
    Documento(
        "KB-02",
        None,
        "Prazo de atendimento de chamados",
        "Chamados de prioridade alta são atendidos em até 4 horas úteis; os demais, em até 2 dias úteis.",
    ),
    Documento(
        "KB-10",
        "padaria-sol",
        "Contrato da Padaria Sol",
        "Contrato de suporte da Padaria Sol: plano Ouro, desconto negociado de 18% até 12/2026.",
    ),
    Documento(
        "KB-20",
        "mercado-lua",
        "Contrato do Mercado Lua",
        "Contrato de suporte do Mercado Lua: plano Prata, multa rescisória de R$ 4.000,00.",
    ),
]

CHAMADOS = {
    "CH-1001": Chamado("CH-1001", "padaria-sol", "Boleto de outubro não chegou", "Ana Souza, (14) 99999-0001"),
    "CH-2001": Chamado("CH-2001", "mercado-lua", "Erro ao emitir nota", "Bruno Lima, (14) 99999-0002"),
}

DOMINIO_DA_EMPRESA = "suporte.exemplo"
