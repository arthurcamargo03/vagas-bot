"""Carrega e valida as configurações do projeto a partir do .env."""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    SEARCH_KEYWORD = os.getenv("SEARCH_KEYWORD", "estagio desenvolvimento")
    SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "90"))
    DB_PATH = os.getenv("DB_PATH", "vagas.db")

    @classmethod
    def validar(cls) -> None:
        """Garante que as variáveis obrigatórias foram configuradas."""
        faltando = []
        if not cls.TELEGRAM_BOT_TOKEN:
            faltando.append("TELEGRAM_BOT_TOKEN")
        if not cls.TELEGRAM_CHAT_ID:
            faltando.append("TELEGRAM_CHAT_ID")
        if faltando:
            raise RuntimeError(
                f"Variáveis de ambiente faltando no .env: {', '.join(faltando)}"
            )
