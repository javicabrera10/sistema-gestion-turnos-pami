"""Crea los recordatorios de los turnos confirmados que se acercan y los avisos de toma de medicación.

Se puede correr a mano o programar (cron en Linux, Programador de tareas en Windows), por ejemplo cada 15 minutos:

    uv run python -m scripts.enviar_recordatorios

Se puede ejecutar las veces que se quiera: cada recordatorio y cada aviso de toma se crean una sola vez.
Para que no se pierdan tomas conviene programarlo cada 15 minutos (los avisos de toma tienen una ventana de 30).
"""

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402
from app.services.recordatorio_service import crear_servicio  # noqa: E402
from app.services.toma_service import crear_servicio_tomas  # noqa: E402


def main():
    app = create_app()
    creados = crear_servicio(app.db, app.event_bus).procesar()
    tomas = crear_servicio_tomas(app.db).procesar()
    print(f"Recordatorios creados: {creados}")
    print(f"Avisos de toma creados: {tomas}")


if __name__ == "__main__":
    main()
