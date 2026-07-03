"""Persistência das vagas já enviadas, para evitar duplicatas."""
import sqlite3
import logging
from contextlib import contextmanager
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Vaga:
    titulo: str
    empresa: str
    link: str
    fonte: str  # "indeed" ou "gupy"


@contextmanager
def _conectar(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def inicializar_db(db_path: str) -> None:
    """Cria a tabela de vagas caso ainda não exista."""
    with _conectar(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS vagas_enviadas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link TEXT UNIQUE NOT NULL,
                titulo TEXT NOT NULL,
                empresa TEXT NOT NULL,
                fonte TEXT NOT NULL,
                enviado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    logger.info("Banco de dados inicializado em %s", db_path)


def ja_foi_enviada(db_path: str, link: str) -> bool:
    """Verifica se uma vaga (identificada pelo link) já foi postada antes."""
    with _conectar(db_path) as conn:
        cursor = conn.execute(
            "SELECT 1 FROM vagas_enviadas WHERE link = ? LIMIT 1", (link,)
        )
        return cursor.fetchone() is not None


def marcar_como_enviada(db_path: str, vaga: Vaga) -> None:
    """Registra a vaga como enviada para não repetir no futuro."""
    with _conectar(db_path) as conn:
        try:
            conn.execute(
                """
                INSERT INTO vagas_enviadas (link, titulo, empresa, fonte)
                VALUES (?, ?, ?, ?)
                """,
                (vaga.link, vaga.titulo, vaga.empresa, vaga.fonte),
            )
        except sqlite3.IntegrityError:
            # Já existe (corrida entre checagem e inserção) — ignora.
            logger.debug("Vaga já registrada, ignorando: %s", vaga.link)
