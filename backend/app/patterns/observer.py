"""Patrón Observer: un bus de eventos muy simple.

Los services publican hechos ("turno.otorgado") y los observers reaccionan. Así el
módulo de turnos no depende del de notificaciones: solo publica lo que pasó.

Un observer que falla no tumba la operación principal: se registra el error y se sigue.
"""

import logging
from collections import defaultdict

log = logging.getLogger("pami.eventos")

# Eventos del Sprint 1
TURNO_SOLICITADO = "turno.solicitado"
TURNO_OTORGADO = "turno.otorgado"
TURNO_CONFIRMADO = "turno.confirmado"
TURNO_RECHAZADO = "turno.rechazado"
RECETA_EMITIDA = "receta.emitida"

# Eventos del Sprint 2: el administrativo cambia un turno ya otorgado
TURNO_REPROGRAMADO = "turno.reprogramado"
TURNO_CANCELADO = "turno.cancelado"

# Eventos del Sprint 3: el sistema recuerda un turno próximo (lo publica el servicio de recordatorios)
TURNO_RECORDATORIO = "turno.recordatorio"


class EventBus:
    def __init__(self):
        self._handlers = defaultdict(list)

    def suscribir(self, evento: str, handler) -> None:
        self._handlers[evento].append(handler)

    def publicar(self, evento: str, datos: dict) -> None:
        for handler in list(self._handlers[evento]):
            try:
                handler(datos)
            except Exception:  # noqa: BLE001 - un observer roto no debe romper el flujo
                # no se loguean los datos: pueden incluir información del paciente
                log.exception("falló el observer %s del evento %s", getattr(handler, "__name__", handler), evento)
