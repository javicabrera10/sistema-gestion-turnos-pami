"""Observers de la aplicación: qué hace el sistema cuando pasa cada evento."""

from bson.errors import InvalidId

from app.patterns.observer import (
    TURNO_CANCELADO,
    TURNO_CONFIRMADO,
    TURNO_OTORGADO,
    TURNO_RECHAZADO,
    TURNO_REPROGRAMADO,
)
from app.repositories.familiar_repository import FamiliarRepository, MensajeFamiliarRepository
from app.repositories.notificacion_repository import NotificacionRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.familiar_service import EVENTOS_PARA_FAMILIAR, FamiliarService
from app.services.notificacion_service import NotificacionService


def registrar_observers(app) -> None:
    """Suscribe los handlers al bus. Se llama una sola vez desde create_app."""
    bus = app.event_bus

    def servicio() -> NotificacionService:
        return NotificacionService(NotificacionRepository(app.db))

    def nombre_del_paciente(datos: dict) -> str | None:
        try:
            paciente = UsuarioRepository(app.db).get_by_id(datos["paciente_id"])
        except InvalidId:
            return None
        return paciente["nombre"] if paciente else None

    def notificar_turno_otorgado(datos: dict) -> None:
        servicio().crear_turno_otorgado(datos)

    def notificar_turno_reprogramado(datos: dict) -> None:
        servicio().crear_turno_reprogramado(datos)

    def notificar_turno_cancelado(datos: dict) -> None:
        servicio().crear_turno_cancelado(datos)

    def notificar_turno_confirmado(datos: dict) -> None:
        servicio().crear_respuesta_paciente(datos, aceptado=True, paciente_nombre=nombre_del_paciente(datos))

    def notificar_turno_rechazado(datos: dict) -> None:
        servicio().crear_respuesta_paciente(datos, aceptado=False, paciente_nombre=nombre_del_paciente(datos))

    bus.suscribir(TURNO_OTORGADO, notificar_turno_otorgado)
    bus.suscribir(TURNO_REPROGRAMADO, notificar_turno_reprogramado)
    bus.suscribir(TURNO_CANCELADO, notificar_turno_cancelado)
    bus.suscribir(TURNO_CONFIRMADO, notificar_turno_confirmado)
    bus.suscribir(TURNO_RECHAZADO, notificar_turno_rechazado)

    def avisar_al_familiar(evento: str):
        """Observer que le avisa al familiar autorizado del paciente cuando pasa `evento` con uno de sus turnos."""

        def handler(datos: dict) -> None:
            familiares = FamiliarService(FamiliarRepository(app.db), MensajeFamiliarRepository(app.db))
            if familiares.obtener(datos["paciente_id"]) is None:
                return  # nadie autorizado: no hace falta ni buscar el nombre del paciente
            familiares.avisar_turno(evento, datos, nombre_del_paciente(datos))

        handler.__name__ = f"avisar_al_familiar[{evento}]"
        return handler

    for evento in EVENTOS_PARA_FAMILIAR:
        bus.suscribir(evento, avisar_al_familiar(evento))
