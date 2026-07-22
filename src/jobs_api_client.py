"""
DEPRECADO (2026-07): substituído por `src/meupadrinho_client.py`.

O bot passou a bater DIRETO na API do Meu Padrinho (sem cold start, com filtro
de Curitiba/remoto e mais volume por ciclo), então este cliente do serviço
api-vagas no Render saiu do pipeline (`buscar_todas_vagas` não o chama mais). A
api-vagas no Render virou redundante e pode ser desligada. Mantido só de
referência / caso queira voltar a usar o serviço separado.

--- (documentação original abaixo) ---

Cliente para o serviço api-vagas (Meu Padrinho) — fonte PRINCIPAL de estágio BR.

api-vagas (https://github.com/matheusaudibert/jobs-api) é uma API Node.js
SEPARADA: roda como serviço próprio (via Docker ou `node index.js`), não é
biblioteca Python. Ela agrega vagas do Meu Padrinho (meupadrinho.com.br),
focado no mercado brasileiro.

Cada rota (/estagio, /junior, /pleno, /senior) devolve só UMA vaga — a mais
recente. Como o dedup por link no SQLite já evita repost, basta bater na rota
a cada ciclo: se a vaga mais recente mudou, ela é nova e será enviada.

A URL base vem de JOBS_API_BASE_URL no .env (default http://localhost:3001),
pra trocar fácil entre rodar local e deploy sem mexer no código.
"""
import logging
import time

import requests

from src.scraper import VagaEncontrada

logger = logging.getLogger(__name__)

# 1ª tentativa usa timeout longo pra absorver o cold start do Render free tier
# (Web Service dorme após ~15 min e leva ~1 min pra acordar). As tentativas
# seguintes já pegam o serviço acordado, então usam o timeout normal.
TIMEOUT_COLD_START_SEGUNDOS = 60
TIMEOUT_SEGUNDOS = 15
TENTATIVAS = 2
ESPERA_ENTRE_TENTATIVAS_SEGUNDOS = 3
FONTE = "meupadrinho"


def _get_com_retry(url: str) -> requests.Response:
    """GET tolerante a cold start: 1ª tentativa com timeout longo, retry curto.

    Lança a última exceção se todas as tentativas falharem — quem chama trata.
    """
    ultimo_erro: Exception | None = None
    for tentativa in range(1, TENTATIVAS + 1):
        timeout = TIMEOUT_COLD_START_SEGUNDOS if tentativa == 1 else TIMEOUT_SEGUNDOS
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            ultimo_erro = e
            if tentativa < TENTATIVAS:
                logger.warning(
                    "api-vagas tentativa %d/%d falhou em %s (%s). Retentando em %ds…",
                    tentativa, TENTATIVAS, url, e, ESPERA_ENTRE_TENTATIVAS_SEGUNDOS,
                )
                time.sleep(ESPERA_ENTRE_TENTATIVAS_SEGUNDOS)
    raise ultimo_erro  # type: ignore[misc]


def _para_vaga(dados: dict) -> VagaEncontrada | None:
    """Converte o JSON do api-vagas no formato comum das fontes do bot."""
    titulo = dados.get("titulo_vaga")
    link = dados.get("link_vaga")
    if not (titulo and link):
        logger.warning("Resposta do api-vagas sem titulo_vaga/link_vaga: %s", dados)
        return None

    local = dados.get("local")
    titulo_final = f"{titulo} — {local}" if local else titulo

    return VagaEncontrada(
        titulo=titulo_final,
        empresa=dados.get("nome_empresa") or "Empresa não informada",
        link=link,
        fonte=FONTE,
    )


def buscar_vagas_api(
    base_url: str, niveis: tuple[str, ...] = ("estagio",)
) -> list[VagaEncontrada]:
    """
    Consulta o serviço api-vagas e devolve a vaga mais recente de cada nível.

    Best-effort: se o serviço estiver fora do ar (não rodando local, deploy
    caiu, timeout, JSON inválido), loga o erro e devolve o que conseguiu — o
    ciclo do bot segue com as outras fontes e NUNCA trava por causa desta.
    """
    vagas: list[VagaEncontrada] = []
    for nivel in niveis:
        url = f"{base_url.rstrip('/')}/{nivel}"
        try:
            resp = _get_com_retry(url)
            vaga = _para_vaga(resp.json())
            if vaga:
                vagas.append(vaga)
        except requests.exceptions.RequestException as e:
            logger.error("api-vagas indisponível em %s: %s", url, e)
        except ValueError as e:
            logger.error("api-vagas retornou JSON inválido em %s: %s", url, e)

    logger.info("api-vagas: %d vaga(s) obtida(s) de %d nível(is).", len(vagas), len(niveis))
    return vagas
