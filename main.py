"""Ponto de entrada do bot de vagas de estágio."""
import logging

from src.scheduler import iniciar_agendador

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

if __name__ == "__main__":
    iniciar_agendador()
