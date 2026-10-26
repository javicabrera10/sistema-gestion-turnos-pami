import logging
from datetime import datetime, time, timedelta

from app.repositories.aviso_toma_repository import AvisoTomaRepository
from app.repositories.notificacion_repository import NotificacionRepository
from app.repositories.receta_repository import RecetaRepository
from app.services.notificacion_service import NotificacionService
from app.services.recordatorio_service import a_hora_local, ahora_local

log = logging.getLogger("pami.tomas")

# Se avisa una toma si su horario cayó en los últimos 30 minutos. Con esta ventana alcanza con ejecutar
# el recordatorio cada 15 minutos; si no se ejecuta a tiempo, esa toma no se avisa más tarde.
VENTANA_MINUTOS = 30


class TomaMedicacionService:
    """Crea un aviso para el paciente a la hora de cada toma de su plan de medicación."""

    def __init__(self, recetas_repo, avisos_repo, notificaciones: NotificacionService, ventana_minutos: int = VENTANA_MINUTOS):
        self.recetas = recetas_repo
        self.avisos = avisos_repo
        self.notificaciones = notificaciones
        self.ventana = timedelta(minutes=ventana_minutos)

    def procesar(self, ahora: datetime | None = None) -> int:
        """Revisa los planes activos y crea los avisos de toma que correspondan. Devuelve cuántos creó.

        Se puede ejecutar todas las veces que se quiera: cada toma (receta, día, medicamento y horario)
        se avisa una sola vez.
        """
        ahora = ahora or ahora_local()
        desde = ahora - self.ventana

        creados = 0
        for receta in self.recetas.listar_con_plan_activo():
            inicio = a_hora_local(receta["inicio_plan"])
            for item in receta["plan_medicacion"]:
                # el tratamiento dura `duracion_dias` días desde que empezó el plan
                fin = inicio + timedelta(days=item["duracion_dias"])
                for horario in item["horarios"]:
                    hora, minuto = (int(parte) for parte in horario.split(":"))
                    # se mira también el día anterior: a las 00:10 la toma de las 23:50 todavía está en la ventana
                    for dia in (ahora.date() - timedelta(days=1), ahora.date()):
                        momento = datetime.combine(dia, time(hora, minuto))
                        if not (desde <= momento <= ahora) or not (inicio <= momento < fin):
                            continue
                        if not self.avisos.registrar(str(receta["_id"]), dia.isoformat(), item["medicamento"], horario):
                            continue  # ya se avisó
                        self.notificaciones.crear_toma_medicacion(
                            {
                                "paciente_id": receta["paciente_id"],
                                "receta_id": str(receta["_id"]),
                                "medicamento": item["medicamento"],
                                "dosis": item["dosis"],
                                "horario": horario,
                            }
                        )
                        creados += 1
        # el log no lleva medicamentos ni pacientes: son datos de salud
        log.info("avisos de toma creados=%s", creados)
        return creados


def crear_servicio_tomas(db) -> TomaMedicacionService:
    """Arma el servicio con su base (lo usan el endpoint y el script de recordatorios)."""
    return TomaMedicacionService(
        RecetaRepository(db), AvisoTomaRepository(db), NotificacionService(NotificacionRepository(db))
    )
