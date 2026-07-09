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
    # URL base do serviço api-vagas (Meu Padrinho), rodado à parte.
    # Local: http://localhost:3001 | Deploy: a URL pública do serviço.
    JOBS_API_BASE_URL = os.getenv("JOBS_API_BASE_URL", "http://localhost:3001")
    # Máximo de vagas enviadas por ciclo (anti-flood).
    MAX_VAGAS_POR_CICLO = int(os.getenv("MAX_VAGAS_POR_CICLO", "8"))
    # Slots do cap reservados só para fontes BR (api-vagas/Gupy/Indeed), para
    # estágio nacional nunca ser espremido pelas fontes globais (Remotive etc).
    RESERVA_VAGAS_BR = int(os.getenv("RESERVA_VAGAS_BR", "3"))

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
