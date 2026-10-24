import logging
import os
from datetime import datetime, timedelta, timezone

from app.patterns.recordatorio_strategy import REGLAS_POR_DEFECTO, reglas_desde_nombres
from app.repositories.notificacion_repository import NotificacionRepository
from app.repositories.turno_repository import TurnoRepository
from app.services.notificacion_service import NotificacionService
from app.services.turno_service import datos_evento

log = logging.getLogger("pami.recordatorios")


def ahora_local() -> datetime:
    """Hora local sin zona horaria, que es como se guardan las fechas de los turnos (la que se ve en pantalla).

    Argentina es UTC-3 todo el año; se puede cambiar con la variable RECORDATORIOS_UTC_OFFSET.
    """
    horas = int(os.getenv("RECORDATORIOS_UTC_OFFSET", "-3"))
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=horas))).replace(tzinfo=None)


class RecordatorioService:
    """Crea un aviso para el paciente cuando se acerca un turno confirmado, según las reglas (Strategy)."""

    def __init__(self, turnos_repo, notificaciones: NotificacionService, reglas=None):
        self.turnos = turnos_repo
        self.notificaciones = notificaciones
        self.reglas = tuple(REGLAS_POR_DEFECTO if reglas is None else reglas)

    def procesar(self, ahora: datetime | None = None) -> int:
        """Revisa los turnos próximos y crea los recordatorios que correspondan. Devuelve cuántos creó.

        Se puede ejecutar todas las veces que se quiera: cada regla se cumple una sola vez por turno.
        """
        if not self.reglas:
            return 0
        ahora = ahora or ahora_local()
        limite = ahora + timedelta(hours=max(r.horas_antes for r in self.reglas))

        creados = 0
        for turno in self.turnos.listar_confirmados_entre(ahora, limite):
            ya_enviadas = set(turno.get("recordatorios_enviados", []))
            aplicables = [
                r for r in self.reglas if r.nombre not in ya_enviadas and r.debe_recordar(turno["fecha_hora"], ahora)
            ]
            if not aplicables:
                continue
            # Un solo aviso por turno aunque apliquen varias reglas a la vez; todas quedan marcadas como cumplidas
            self.notificaciones.crear_recordatorio(datos_evento(turno))
            self.turnos.marcar_recordatorios_enviados(turno["_id"], [r.nombre for r in aplicables])
            creados += 1
        log.info("recordatorios creados=%s", creados)
        return creados


def crear_servicio(db) -> RecordatorioService:
    """Arma el servicio con su base. Las reglas se pueden elegir con RECORDATORIOS_REGLAS (ej: "24h,2h")."""
    texto = os.getenv("RECORDATORIOS_REGLAS", "").strip()
    reglas = reglas_desde_nombres(texto) if texto else None
    return RecordatorioService(TurnoRepository(db), NotificacionService(NotificacionRepository(db)), reglas)
