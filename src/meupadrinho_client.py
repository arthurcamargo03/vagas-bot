"""
Cliente do Meu Padrinho (meupadrinho.com.br) — fonte PRINCIPAL de estágio BR.

Substitui o antigo `jobs_api_client.py` (que dependia do serviço api-vagas
hospedado no Render). Agora batemos DIRETO na API pública do Meu Padrinho:
pegamos a LISTA de estágios recentes e filtramos por localização/modalidade
aqui no Python.

Regra de filtro (o que interessa pra quem mora em Curitiba):
  - LOCAL: `forma_trabalho == 'remoto'` -> mantém (remoto Brasil); Curitiba OU
    região metropolitana (presencial/híbrido) -> mantém; outra cidade -> descarta.
  - TIPO: barra freelance e bolsa de pós (mestrado/doutorado/pós-graduação),
    mesmo sendo "estágio" — o canal é estágio pra graduação. Checado no título
    da própria lista, antes de gastar um request de detalhe.

Por que trocar o api-vagas por isto (decisão 2026-07):
  - Sem cold start: o Meu Padrinho é site de produção, sempre no ar (o api-vagas
    no Render free dormia e levava ~1 min pra acordar).
  - Mais volume: a lista traz ~10 vagas/ciclo, não só a mais recente — dá pra
    manter TODAS as de Curitiba/remoto de uma vez (o dedup no SQLite cuida do
    repost). O api-vagas só expunha 1 vaga por nível.

Detalhe de custo: `local` e `link_vaga` só existem no endpoint de DETALHES, então
é 1 request de lista + 1 request de detalhe por vaga da página. Best-effort: se
o Meu Padrinho cair ou um detalhe falhar, loga e segue — o ciclo nunca trava.
"""
import logging
import time
import unicodedata

import requests

from src.scraper import VagaEncontrada

logger = logging.getLogger(__name__)

BASE_URL = "https://meupadrinho.com.br/api"
TIMEOUT_SEGUNDOS = 20
DELAY_ENTRE_DETALHES_SEGUNDOS = 0.5
FONTE = "meupadrinho"

# Curitiba + região metropolitana (nomes JÁ normalizados: minúsculo, sem acento).
_CURITIBA_REGIAO = (
    "curitiba", "pinhais", "sao jose dos pinhais", "colombo", "araucaria",
    "campo largo", "fazenda rio grande", "almirante tamandare", "piraquara",
    "quatro barras", "campina grande do sul",
)

# Tipos que NÃO interessam mesmo aparecendo como "estágio": freelance avulso e
# bolsa de pós-graduação (mestrado/doutorado). O canal é estágio pra graduação.
# Termos JÁ normalizados (minúsculo, sem acento) — comparados por substring, o
# que cobre variações ("freelance"/"freelancer"). NÃO incluímos "bolsa"/"bolsista"
# sozinhos de propósito: estágio no Brasil costuma ser "bolsa-auxílio", legítimo.
_TITULO_INDESEJADO = (
    "freelance", "freela", "mestrado", "doutorado", "pos-graduacao",
)


def _normalizar(texto: str | None) -> str:
    """minúsculo + sem acento — casa 'Curitiba'/'híbrido' de forma robusta."""
    nfkd = unicodedata.normalize("NFD", texto or "")
    sem_acento = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    return sem_acento.lower().strip()


def _local_interessa(local: str | None, forma_trabalho: str | None) -> bool:
    """True se a vaga interessa pra quem mora em Curitiba.

    Remoto vale de qualquer lugar do Brasil (dá pra fazer de Curitiba). Caso
    contrário (presencial/híbrido/sem modalidade), só interessa se for em
    Curitiba ou na região metropolitana.
    """
    if _normalizar(forma_trabalho) == "remoto":
        return True
    local_norm = _normalizar(local)
    return any(cidade in local_norm for cidade in _CURITIBA_REGIAO)


def _tipo_indesejado(titulo: str | None) -> bool:
    """True se o título indica freelance ou bolsa de pós (mestrado/doutorado)."""
    titulo_norm = _normalizar(titulo)
    return any(termo in titulo_norm for termo in _TITULO_INDESEJADO)


def _get_json(url: str) -> dict:
    resp = requests.get(url, timeout=TIMEOUT_SEGUNDOS)
    resp.raise_for_status()
    return resp.json()


def _montar_vaga(detalhes: dict) -> VagaEncontrada | None:
    """Converte os detalhes do Meu Padrinho no formato comum das fontes."""
    titulo = detalhes.get("titulo_vaga")
    link = detalhes.get("link_vaga")
    if not (titulo and link):
        return None

    local = detalhes.get("local")
    titulo_final = f"{titulo} — {local}" if local else titulo
    return VagaEncontrada(
        titulo=titulo_final,
        empresa=detalhes.get("nome_empresa") or "Empresa não informada",
        link=link,
        fonte=FONTE,
    )


def buscar_vagas_meupadrinho(nivel: str = "estagio") -> list[VagaEncontrada]:
    """
    Busca estágios recentes no Meu Padrinho e mantém só os de Curitiba/remoto.

    Best-effort: se a API cair (timeout, JSON inválido) devolve o que conseguiu
    e o ciclo do bot segue com as outras fontes, sem nunca travar por esta.
    """
    try:
        lista = _get_json(f"{BASE_URL}/vagas?niveis={nivel}&page=0").get("vagas", [])
    except (requests.exceptions.RequestException, ValueError) as e:
        logger.error("Meu Padrinho indisponível ao listar '%s': %s", nivel, e)
        return []

    alvo = _normalizar(nivel)
    mantidas: list[VagaEncontrada] = []
    fora_local = 0
    tipo_ruim = 0
    for item in lista:
        # Pula encerradas e níveis que não batem com o pedido (a API às vezes
        # mistura; o campo vem como string "True"/"False").
        if str(item.get("vaga_encerrada")).lower() == "true":
            continue
        if _normalizar(item.get("nivel")) != alvo:
            continue

        # Filtro de TIPO no título da própria lista — barra freelance/pós antes
        # de gastar um request de detalhe.
        titulo_lista = item.get("titulo_vaga")
        if _tipo_indesejado(titulo_lista):
            tipo_ruim += 1
            logger.debug("Meu Padrinho descartada (freelance/pós): %s", titulo_lista)
            continue

        nano_id = item.get("nano_id")
        if not nano_id:
            continue

        try:
            detalhes = _get_json(f"{BASE_URL}/vagas/{nano_id}")
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.warning("Meu Padrinho: falha ao detalhar %s: %s", nano_id, e)
            continue
        finally:
            time.sleep(DELAY_ENTRE_DETALHES_SEGUNDOS)

        if not _local_interessa(detalhes.get("local"), detalhes.get("forma_trabalho")):
            fora_local += 1
            logger.debug(
                "Meu Padrinho descartada (fora de Curitiba/remoto): %s [%s / %s]",
                detalhes.get("titulo_vaga"), detalhes.get("local"),
                detalhes.get("forma_trabalho"),
            )
            continue

        vaga = _montar_vaga(detalhes)
        if vaga:
            mantidas.append(vaga)

    logger.info(
        "Meu Padrinho (%s): %d brutas → %d mantidas (Curitiba/remoto) + %d fora "
        "de local + %d tipo indesejado (freelance/pós).",
        nivel, len(lista), len(mantidas), fora_local, tipo_ruim,
    )
    return mantidas
