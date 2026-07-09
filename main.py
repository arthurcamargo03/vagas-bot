"""Ponto de entrada do bot: roda UM ciclo completo e termina.

O agendamento é EXTERNO — quem dispara é o cron do GitHub Actions (ver
.github/workflows/rodar-bot.yml), um ciclo por execução. Não há mais loop
nem processo de longa duração; por isso o antigo BlockingScheduler saiu.

Fluxo do ciclo: validar config -> inicializar o banco (se preciso) -> buscar
todas as fontes -> filtrar as novas -> enviar ao Telegram -> marcar enviadas.

Códigos de saída (importantes pro Actions marcar a run verde/vermelha):
- 0: ciclo concluído (mesmo que 0 vagas novas, ou que UMA fonte tenha falhado —
     falha de fonte isolada é tratada lá dentro e NÃO derruba o ciclo).
- 1: falha crítica (config ausente, banco inacessível, erro inesperado geral).
"""
import logging
import sys

from src.config import Config
from src.scheduler import executar_ciclo_unico
from src.storage import inicializar_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def main() -> int:
    try:
        Config.validar()
        inicializar_db(Config.DB_PATH)
        executar_ciclo_unico()
    except Exception:
        logger.exception("Falha crítica: ciclo abortado.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
