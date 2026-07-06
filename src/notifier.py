"""Postagem de vagas no Telegram."""
import logging

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from src.scraper import VagaEncontrada

logger = logging.getLogger(__name__)


def _formatar_mensagem(vaga: VagaEncontrada) -> str:
    return (
        f"💼 *{vaga.titulo}*\n"
        f"🏢 {vaga.empresa}\n"
        f"🔗 [Ver vaga]({vaga.link})\n"
        f"📌 Fonte: {vaga.fonte.capitalize()}"
    )


async def enviar_vaga(bot_token: str, chat_id: str, vaga: VagaEncontrada) -> bool:
    """Envia uma vaga para o canal/grupo do Telegram. Retorna True se enviou com sucesso."""
    bot = Bot(token=bot_token)
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=_formatar_mensagem(vaga),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=False,
        )
        logger.info("Vaga enviada ao Telegram: %s (%s)", vaga.titulo, vaga.fonte)
        return True
    except TelegramError as e:
        logger.error("Falha ao enviar vaga ao Telegram: %s", e)
        return False
