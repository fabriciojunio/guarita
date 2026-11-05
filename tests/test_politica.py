from pathlib import Path

import pytest

from guarita.politica import PoliticaInvalida, carregar_politica, ler_politica

VALIDA = 'somente_leitura = ["ler_chamado"]\nlimite_de_acoes = 5\nlimite_do_resultado = 4000\n'


def test_politica_que_vem_com_o_pacote() -> None:
    politica = carregar_politica()
    assert politica.somente_leitura == frozenset({"ler_chamado"})
    assert politica.limite_de_acoes == 5
    assert politica.limite_do_resultado == 4000


def test_politica_de_arquivo(tmp_path: Path) -> None:
    arquivo = tmp_path / "p.toml"
    arquivo.write_text(VALIDA.replace("5", "3"), encoding="utf-8")
    assert carregar_politica(arquivo).limite_de_acoes == 3


@pytest.mark.parametrize(
    ("texto", "erro"),
    [
        (VALIDA.replace("somente_leitura", "somente_leiura"), "chave desconhecida"),
        (VALIDA + "aprovar_tudo = true\n", "chave desconhecida"),
        ("limite_de_acoes = 5\nlimite_do_resultado = 4000\n", "chave faltando"),
        (VALIDA.replace("= 5", "= 0"), "limite_de_acoes"),
        (VALIDA.replace("= 5", "= 500"), "limite_de_acoes"),
        (VALIDA.replace("= 5", "= true"), "limite_de_acoes"),
        (VALIDA.replace("= 5", '= "5"'), "limite_de_acoes"),
        (VALIDA.replace("4000", "10"), "limite_do_resultado"),
        (VALIDA.replace('["ler_chamado"]', '"ler_chamado"'), "lista"),
        (VALIDA.replace('["ler_chamado"]', '["ler chamado; rm"]'), "lista"),
        ("isto não é toml", "TOML inválido"),
    ],
)
def test_politica_com_erro_e_recusada_inteira(texto: str, erro: str) -> None:
    with pytest.raises(PoliticaInvalida, match=erro):
        ler_politica(texto)
