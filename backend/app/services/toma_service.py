import logging
from datetime import datetime, timezone

from app.repositories.notificacion_repository import NotificacionRepository
from app.repositories.receta_repository import RecetaRepository
from app.services.notificacion_service import NotificacionService

log = logging.getLogger("pami.tomas")


class TomaMedicacionService:
    """Le entrega al paciente su receta y el plan de toma cuando el administrativo genera los recordatorios.

    El aviso sale una sola vez por receta, en el momento en que el administrativo toca el botón
    (no a la hora de cada toma).
    """

    def __init__(self, recetas_repo, notificaciones: NotificacionService):
        self.recetas = recetas_repo
        self.notificaciones = notificaciones

    def procesar(self, ahora: datetime | None = None) -> int:
        """Crea el aviso de las recetas emitidas con plan que todavía no lo tienen. Devuelve cuántos creó.

        Se puede ejecutar todas las veces que se quiera: cada receta se avisa una sola vez.
        """
        # Mongo guarda datetimes en UTC sin zona horaria (igual que en el resto de la app)
        ahora = ahora or datetime.now(timezone.utc).replace(tzinfo=None)

        creados = 0
        for receta in self.recetas.listar_pendientes_de_recordatorio():
            if not self.recetas.reclamar_recordatorio(receta["_id"], ahora):
                continue  # otro administrativo ya lo generó
            receta_id = str(receta["_id"])
            self.notificaciones.crear_toma_medicacion(
                {
                    "paciente_id": receta["paciente_id"],
                    "receta_id": receta_id,
                    "plan": receta["plan_medicacion"],
                    "indicaciones": receta.get("indicaciones", ""),
                }
            )
            self.notificaciones.resolver_receta_emitida(receta_id)
            creados += 1
        # el log no lleva medicamentos ni pacientes: son datos de salud
        log.info("avisos de receta y toma creados=%s", creados)
        return creados


def crear_servicio_tomas(db) -> TomaMedicacionService:
    """Arma el servicio con su base (lo usa el endpoint de recordatorios)."""
    return TomaMedicacionService(RecetaRepository(db), NotificacionService(NotificacionRepository(db)))
