"""
Scraping de vagas de estágio no Indeed e na Gupy.

IMPORTANTE: os seletores CSS/HTML usados aqui são um ponto de partida.
Indeed e Gupy mudam a estrutura das páginas com frequência e possuem
proteção anti-bot — espere que isso quebre e precise de ajuste. Rode
`ver_html_bruto()` para inspecionar a página atual quando algo parar
de funcionar.
"""
import logging
import time
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
}

DELAY_ENTRE_REQUISICOES_SEGUNDOS = 3


@dataclass
class VagaEncontrada:
    titulo: str
    empresa: str
    link: str
    fonte: str


def _requisitar(url: str, params: dict | None = None) -> requests.Response | None:
    """Faz a requisição HTTP com tratamento de erro. Retorna None em falha."""
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        return resp
    except requests.exceptions.RequestException as e:
        logger.error("Falha ao requisitar %s: %s", url, e)
        return None
    finally:
        time.sleep(DELAY_ENTRE_REQUISICOES_SEGUNDOS)


def buscar_vagas_indeed(keyword: str, localizacao: str = "Brasil") -> list[VagaEncontrada]:
    """
    Busca vagas no Indeed por palavra-chave.

    TODO: validar os seletores abaixo contra o HTML real — a estrutura
    de cards de vaga do Indeed muda com frequência. Use
    `ver_html_bruto("https://br.indeed.com/jobs?q=...")` para conferir.
    """
    vagas: list[VagaEncontrada] = []
    url = "https://br.indeed.com/jobs"
    params = {"q": keyword, "l": localizacao}

    resp = _requisitar(url, params=params)
    if resp is None:
        return vagas

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select("div.job_seen_beacon")  # TODO: confirmar seletor atual

    for card in cards:
        try:
            titulo_el = card.select_one("h2.jobTitle span")
            empresa_el = card.select_one("span.companyName")
            link_el = card.select_one("a")

            if not (titulo_el and empresa_el and link_el):
                continue

            link_relativo = link_el.get("href", "")
            link = f"https://br.indeed.com{link_relativo}"

            vagas.append(
                VagaEncontrada(
                    titulo=titulo_el.get_text(strip=True),
                    empresa=empresa_el.get_text(strip=True),
                    link=link,
                    fonte="indeed",
                )
            )
        except Exception as e:
            logger.warning("Erro ao parsear um card de vaga do Indeed: %s", e)
            continue

    logger.info("Indeed: %d vagas encontradas para '%s'", len(vagas), keyword)
    return vagas


def buscar_vagas_gupy(keyword: str) -> list[VagaEncontrada]:
    """
    Busca vagas na Gupy por palavra-chave.

    TODO: a Gupy costuma expor um endpoint JSON não documentado
    (verifique a aba Network do navegador em vagas.gupy.io ao pesquisar)
    que é mais estável que fazer parsing de HTML. Ajuste esta função
    assim que identificar o endpoint correto.
    """
    vagas: list[VagaEncontrada] = []
    url = "https://portal.gupy.io/job-search/term"
    params = {"term": keyword}

    resp = _requisitar(url, params=params)
    if resp is None:
        return vagas

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.select("a[data-testid='job-list__listitem-link']")  # TODO: confirmar seletor

    for card in cards:
        try:
            titulo_el = card.select_one("h3")
            empresa_el = card.select_one("p")
            link_relativo = card.get("href", "")

            if not (titulo_el and empresa_el and link_relativo):
                continue

            vagas.append(
                VagaEncontrada(
                    titulo=titulo_el.get_text(strip=True),
                    empresa=empresa_el.get_text(strip=True),
                    link=f"https://portal.gupy.io{link_relativo}",
                    fonte="gupy",
                )
            )
        except Exception as e:
            logger.warning("Erro ao parsear um card de vaga da Gupy: %s", e)
            continue

    logger.info("Gupy: %d vagas encontradas para '%s'", len(vagas), keyword)
    return vagas


def ver_html_bruto(url: str, params: dict | None = None) -> str:
    """Utilitário de debug: retorna o HTML bruto de uma URL para inspeção manual."""
    resp = _requisitar(url, params=params)
    return resp.text if resp else ""
