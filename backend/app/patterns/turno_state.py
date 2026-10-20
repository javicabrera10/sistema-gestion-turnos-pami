"""Patrón State para los estados de un turno.

Cada estado es una clase que sabe a qué estado se puede pasar desde él.
Si la acción no está permitida, lanza TransicionInvalida. Así las reglas del
flujo viven en un solo lugar y el servicio no necesita una cadena de if/else.

Flujo actual:
    SOLICITADO --otorgar--> OTORGADO --confirmar--> CONFIRMADO
                                     --rechazar---> RECHAZADO
"""

from app.models.turno import EstadoTurno


class TransicionInvalida(Exception):
    pass


class EstadoState:
    estado: EstadoTurno

    def _invalida(self, accion: str):
        raise TransicionInvalida(
            f"No se puede {accion} un turno que está {self.estado.value}"
        )

    # Cada método devuelve el EstadoTurno al que pasa el turno.
    def otorgar(self) -> EstadoTurno:
        self._invalida("otorgar")

    def confirmar(self) -> EstadoTurno:
        self._invalida("confirmar")

    def rechazar(self) -> EstadoTurno:
        self._invalida("rechazar")


class Solicitado(EstadoState):
    estado = EstadoTurno.SOLICITADO

    def otorgar(self) -> EstadoTurno:
        return EstadoTurno.OTORGADO


class Otorgado(EstadoState):
    estado = EstadoTurno.OTORGADO

    def confirmar(self) -> EstadoTurno:
        return EstadoTurno.CONFIRMADO

    def rechazar(self) -> EstadoTurno:
        return EstadoTurno.RECHAZADO


# Estados sin salida por ahora (reprogramar y cancelar llegan en el Sprint 2)
class Confirmado(EstadoState):
    estado = EstadoTurno.CONFIRMADO


class Rechazado(EstadoState):
    estado = EstadoTurno.RECHAZADO


class Reprogramado(EstadoState):
    estado = EstadoTurno.REPROGRAMADO


class Cancelado(EstadoState):
    estado = EstadoTurno.CANCELADO


_ESTADOS = {
    e.estado: e
    for e in (Solicitado(), Otorgado(), Confirmado(), Rechazado(), Reprogramado(), Cancelado())
}


def estado_de(estado) -> EstadoState:
    """Devuelve el objeto State para un EstadoTurno o para el texto guardado en Mongo."""
    return _ESTADOS[EstadoTurno(estado)]
