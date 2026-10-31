"""Crea los recordatorios de los turnos confirmados que se acercan.

Se puede correr a mano o programar (cron en Linux, Programador de tareas en Windows), por ejemplo cada 15 minutos:

    uv run python -m scripts.enviar_recordatorios

Se puede ejecutar las veces que se quiera: cada recordatorio se crea una sola vez.
La receta y el plan de toma del paciente NO se generan acá: los genera el administrativo con el botón
"Generar recordatorios" del panel.
"""

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402
from app.services.recordatorio_service import crear_servicio  # noqa: E402


def main():
    app = create_app()
    creados = crear_servicio(app.db, app.event_bus).procesar()
    print(f"Recordatorios creados: {creados}")


if __name__ == "__main__":
    main()
