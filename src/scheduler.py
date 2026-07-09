"""Orquestra o ciclo completo: raspar -> filtrar novas -> enviar -> agendar."""
import asyncio
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import Config
from src.notifier import enviar_vaga
from src.scraper import buscar_todas_vagas
from src.storage import Vaga, inicializar_db, ja_foi_enviada, marcar_como_enviada

logger = logging.getLogger(__name__)

# Limite de vagas enviadas por ciclo. Evita floodar o canal quando o banco
# está vazio (primeira execução) ou quando uma fonte devolve muita coisa.
MAX_VAGAS_POR_CICLO = 8


async def _processar_e_enviar_vagas() -> None:
    todas_vagas = buscar_todas_vagas(Config.SEARCH_KEYWORD)

    novas = 0
    for vaga in todas_vagas:
        if novas >= MAX_VAGAS_POR_CICLO:
            logger.info("Limite de %d vagas por ciclo atingido.", MAX_VAGAS_POR_CICLO)
            break

        if ja_foi_enviada(Config.DB_PATH, vaga.link):
            continue

        enviada = await enviar_vaga(Config.TELEGRAM_BOT_TOKEN, Config.TELEGRAM_CHAT_ID, vaga)
        if enviada:
            marcar_como_enviada(
                Config.DB_PATH,
                Vaga(titulo=vaga.titulo, empresa=vaga.empresa, link=vaga.link, fonte=vaga.fonte),
            )
            novas += 1

    logger.info("Ciclo concluído: %d vaga(s) nova(s) enviada(s).", novas)


def ciclo_de_verificacao() -> None:
    """Wrapper síncrono chamado pelo agendador (APScheduler não é async-nativo aqui)."""
    asyncio.run(_processar_e_enviar_vagas())


def iniciar_agendador() -> None:
    Config.validar()
    inicializar_db(Config.DB_PATH)

    scheduler = BlockingScheduler(timezone="America/Sao_Paulo")
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
