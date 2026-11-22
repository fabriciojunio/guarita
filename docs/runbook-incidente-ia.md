# Runbook: incidente no assistente

> Dados simulados. Nomes de pessoas, equipes e prazos são do cenário fictício do projeto.

Cada alerta do `python -m guarita.deteccao` aponta para uma seção daqui. O formato é o mesmo em todas:
o que o alerta quer dizer, o que fazer nos primeiros 15 minutos, como investigar e quando o caso vira
incidente de dado pessoal.

Regra geral: o log de auditoria não guarda argumento de ferramenta nem texto de pergunta, de
propósito. Para saber **o que** foi tentado, o caminho é o documento ou a ferramenta envolvida, não o
log.

## Ferramenta trocada

**Alerta:** `ferramenta fora da lista aprovada` (crítica).

O servidor MCP passou a oferecer uma ferramenta, ou uma descrição, diferente da que foi revisada e
aprovada por hash. É o padrão de *rug pull*: o servidor ganha confiança e depois muda.

Primeiros 15 minutos:

1. O agente já recusou a sessão inteira (a defesa levanta `FerramentaNaoAprovada`). Confirme no log
   que não há `executada` depois do alerta para a mesma ferramenta.
2. Suspenda o servidor MCP envolvido até a revisão. Se é de terceiro, avise o fornecedor.

Investigação: compare a descrição atual com a aprovada (`impressao_digital` mostra o hash de cada
uma). Procure no texto novo instruções para o modelo, como `CHAMAR` ou pedido de enviar dado.

Só volta a aprovar depois de revisar a ferramenta nova inteira, nunca reaproveitando o hash antigo.

## Extração do prompt

**Alerta:** `tentativa de extrair as instruções` (alta).

O canário das instruções apareceu na resposta: algum texto fez o modelo repetir o prompt de sistema.
A resposta foi trocada por uma recusa, então nada saiu.

Primeiros 15 minutos: identifique o documento recuperado na pergunta e retire-o da base até a revisão.

Investigação: o prompt da versão defendida não tem segredo, então o dano direto é nenhum. O que
importa é o documento: quem publicou, por qual canal, e se há outros do mesmo autor.

## Sessão sob injeção

**Alerta:** `negações repetidas na mesma janela` (alta).

Três ou mais ações negadas para o mesmo usuário em dez minutos. Usuário distraído nega uma vez; um
documento envenenado faz o modelo tentar a mesma ação a cada pergunta.

Primeiros 15 minutos:

1. Veja quais ferramentas foram negadas e por qual motivo (`usuário não confirmou`, `limite de ações`).
2. Ache o documento em comum nas perguntas da janela e retire-o da base.
3. Pergunte ao usuário se ele confirmou alguma ação que não pediu. Se confirmou, trate como possível
   vazamento (abaixo).

## Ações em laço

**Alerta:** `pergunta disparou ações demais` (média).

Uma pergunta chegou ao limite de ações. Pode ser documento com chamadas em sequência ou um modelo
preso em laço. Revise o documento recuperado; se o padrão se repetir, ele vira o caso anterior.

## Quando vira incidente de dado pessoal

Se o log mostrar `executada` para uma ferramenta que leva dado para fora (como `enviar_email`) logo
depois de um dos alertas acima, trate como possível vazamento de dado pessoal:

1. Descubra o destino e o conteúdo pela ferramenta (a caixa de saída, no caso do e-mail).
2. Avise o encarregado de dados. Pela LGPD, incidente que possa causar risco ou dano relevante ao
   titular precisa ser comunicado à ANPD e ao titular; o encarregado decide com base no que saiu.
3. Registre a linha do tempo com os momentos do log de auditoria, que estão em UTC.

## Depois do incidente

Todo incidente vira um teste novo em `tests/test_ataques.py`, com a versão vulnerável e a defendida,
como os achados GUA-01 a GUA-09. Defesa sem teste volta a quebrar.
