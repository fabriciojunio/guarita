import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from guarita.deteccao import Evento, detectar, ler, principal
from tests.conftest import montar
from tests.test_ataques import ARTIGO_ENVENENADO, ARTIGO_PEDE_INSTRUCOES

INICIO = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


def evento(minuto: float, decisao: str, usuario: str = "ana", ferramenta: str = "enviar_email") -> Evento:
    return Evento(INICIO + timedelta(minutes=minuto), usuario, ferramenta, decisao)


def test_uma_negacao_sozinha_nao_e_incidente() -> None:
    assert detectar([evento(0, "negada: usuário não confirmou"), evento(1, "executada")]) == []


def test_tres_negacoes_em_dez_minutos_viram_alerta_alto() -> None:
    alertas = detectar([evento(m, "negada: usuário não confirmou") for m in (0, 4, 9)])
    assert [(a.regra, a.severidade, a.eventos) for a in alertas] == [("negações repetidas na mesma janela", "alta", 3)]
    assert alertas[0].runbook == "#sessao-sob-injecao"


def test_negacoes_espalhadas_fora_da_janela_nao_alertam() -> None:
    assert detectar([evento(m, "negada: usuário não confirmou") for m in (0, 11, 22)]) == []


def test_ataque_longo_vira_poucos_alertas_e_nao_um_por_evento() -> None:
    alertas = detectar([evento(m * 0.5, "negada: usuário não confirmou") for m in range(9)])
    assert len(alertas) == 3


def test_negacoes_de_usuarios_diferentes_nao_se_somam() -> None:
    eventos = [evento(0, "negada: x", "ana"), evento(1, "negada: x", "bruno"), evento(2, "negada: x", "carla")]
    assert detectar(eventos) == []


def test_ferramenta_trocada_e_critica_e_vem_primeiro() -> None:
    alertas = detectar(
        [
            evento(0, "bloqueada: vazamento das instruções", ferramenta="resposta"),
            evento(1, "negada: ferramenta não aprovada", ferramenta="ler_chamado"),
        ]
    )
    assert [a.severidade for a in alertas] == ["crítica", "alta"]


def test_limite_de_acoes_e_media() -> None:
    alertas = detectar([evento(0, "negada: limite de ações")])
    assert [(a.severidade, a.runbook) for a in alertas] == [("média", "#acoes-em-laco")]


def test_log_adulterado_e_recusado_e_nao_ignorado() -> None:
    with pytest.raises(ValueError, match="linha 2"):
        ler(['{"momento": "2026-11-05T12:00:00+00:00", "usuario": "a", "ferramenta": "f", "decisao": "d"}', "lixo"])


@pytest.mark.anyio
async def test_auditoria_real_dos_ataques_dispara_as_regras(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    caplog.set_level(logging.INFO, "guarita.auditoria")
    async with montar(defendido=True, extras=[ARTIGO_ENVENENADO, ARTIGO_PEDE_INSTRUCOES]) as c:
        for _ in range(3):
            await c.agente.perguntar("Como tiro a segunda via do boleto?")
        await c.agente.perguntar("Tem desconto no boleto?")
    log = tmp_path / "auditoria.jsonl"
    log.write_text("\n".join(r.getMessage() for r in caplog.records if r.name == "guarita.auditoria"), encoding="utf-8")

    assert principal([str(log)]) == 1
    saida = capsys.readouterr().out
    assert "[alta] negações repetidas na mesma janela" in saida
    assert "[alta] tentativa de extrair as instruções" in saida
    assert "99999" not in saida


def test_log_sem_alerta_sai_zero(tmp_path: Path) -> None:
    log = tmp_path / "a.jsonl"
    log.write_text(
        json.dumps({"momento": INICIO.isoformat(), "usuario": "ana", "ferramenta": "f", "decisao": "executada"}),
        encoding="utf-8",
    )
    assert principal([str(log)]) == 0


def test_uso_errado_e_arquivo_ausente_saem_dois(tmp_path: Path) -> None:
    assert principal([]) == 2
    assert principal([str(tmp_path / "nao-existe.jsonl")]) == 2
