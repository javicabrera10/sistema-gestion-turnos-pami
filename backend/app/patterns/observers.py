"""Observers de la aplicación: qué hace el sistema cuando pasa cada evento."""

from app.patterns.observer import TURNO_OTORGADO
from app.repositories.notificacion_repository import NotificacionRepository
from app.services.notificacion_service import NotificacionService


def registrar_observers(app) -> None:
    """Suscribe los handlers al bus. Se llama una sola vez desde create_app."""
    bus = app.event_bus

    def notificar_turno_otorgado(datos: dict) -> None:
        NotificacionService(NotificacionRepository(app.db)).crear_turno_otorgado(datos)

    bus.suscribir(TURNO_OTORGADO, notificar_turno_otorgado)
