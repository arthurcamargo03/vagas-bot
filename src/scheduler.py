"""Orquestra o ciclo completo: raspar -> filtrar novas -> enviar -> agendar."""
import asyncio
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import Config
from src.notifier import enviar_vaga
from src.scraper import buscar_todas_vagas
from src.storage import Vaga, inicializar_db, ja_foi_enviada, marcar_como_enviada

logger = logging.getLogger(__name__)

# Fontes focadas no mercado brasileiro (prioridade). As demais (Remotive,
# Arbeitnow) são globais/remotas e entram só para complementar.
FONTES_BR = {"meupadrinho", "gupy", "indeed"}


async def _enviar_e_marcar(vaga) -> bool:
    """Envia uma vaga nova e a registra no SQLite. True se enviou."""
    if ja_foi_enviada(Config.DB_PATH, vaga.link):
        return False
    enviada = await enviar_vaga(Config.TELEGRAM_BOT_TOKEN, Config.TELEGRAM_CHAT_ID, vaga)
    if enviada:
        marcar_como_enviada(
            Config.DB_PATH,
            Vaga(titulo=vaga.titulo, empresa=vaga.empresa, link=vaga.link, fonte=vaga.fonte),
        )
    return enviada


async def _processar_e_enviar_vagas() -> None:
    todas_vagas = buscar_todas_vagas(Config.SEARCH_KEYWORD)

    # Separa BR (prioritárias) de globais (complementares).
    br = [v for v in todas_vagas if v.fonte in FONTES_BR]
    globais = [v for v in todas_vagas if v.fonte not in FONTES_BR]

    max_total = Config.MAX_VAGAS_POR_CICLO
    reserva_br = min(Config.RESERVA_VAGAS_BR, max_total)
    # Globais nunca ocupam os slots reservados: no máximo (cap - reserva).
    max_globais = max_total - reserva_br

    enviadas = 0
    enviadas_globais = 0

    # Fase 1: vagas BR primeiro, podem usar o cap inteiro (prioridade total).
    for vaga in br:
        if enviadas >= max_total:
            break
        if await _enviar_e_marcar(vaga):
            enviadas += 1

    # Fase 2: globais preenchem o resto, limitadas a (cap - reserva_br), para
    # o canal não virar só vaga global mesmo em ciclos cheios.
    for vaga in globais:
        if enviadas >= max_total or enviadas_globais >= max_globais:
            break
        if await _enviar_e_marcar(vaga):
            enviadas += 1
            enviadas_globais += 1

    logger.info(
        "Ciclo concluído: %d vaga(s) enviada(s) (%d BR + %d globais). "
        "Fonte pool: %d BR, %d globais.",
        enviadas, enviadas - enviadas_globais, enviadas_globais, len(br), len(globais),
    )


def ciclo_de_verificacao() -> None:
    """Wrapper síncrono chamado pelo agendador (APScheduler não é async-nativo aqui).

    Blinda o ciclo: qualquer erro inesperado é logado, mas NÃO derruba o
    processo — o agendador segue e tenta de novo no próximo intervalo.
    """
    try:
        asyncio.run(_processar_e_enviar_vagas())
    except Exception:
        logger.exception("Erro inesperado durante o ciclo de verificação (seguindo).")


def iniciar_agendador() -> None:
    Config.validar()
    inicializar_db(Config.DB_PATH)

    scheduler = BlockingScheduler(timezone=Config.TIMEZONE)
    # Sem next_run_time explícito: o APScheduler agenda o primeiro disparo para
    # daqui a SCRAPE_INTERVAL_MINUTES. A execução imediata abaixo cobre o "agora",
    # então não há disparo duplicado no arranque.
    scheduler.add_job(
        ciclo_de_verificacao,
        "interval",
        minutes=Config.SCRAPE_INTERVAL_MINUTES,
    )

    logger.info(
        "Agendador iniciado. Verificando vagas a cada %d minutos.",
        Config.SCRAPE_INTERVAL_MINUTES,
    )

    # Primeira execução imediata, antes de esperar o primeiro intervalo.
    ciclo_de_verificacao()

    scheduler.start()
