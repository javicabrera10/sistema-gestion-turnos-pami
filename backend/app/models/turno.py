from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EstadoTurno(str, Enum):
    SOLICITADO = "solicitado"  # el paciente pidió el turno
    OTORGADO = "otorgado"  # el administrativo asignó fecha y hora, falta la respuesta del paciente
    CONFIRMADO = "confirmado"  # el paciente aceptó el turno
    RECHAZADO = "rechazado"  # el paciente rechazó el turno
    REPROGRAMADO = "reprogramado"
    CANCELADO = "cancelado"


@dataclass
class Turno:
    paciente_id: str
    especialidad: str
    fecha_hora: datetime  # fecha pedida por el paciente; el administrativo la confirma o la cambia al otorgar
    motivo: str
    estado: EstadoTurno = EstadoTurno.SOLICITADO
    medico_id: str | None = None  # se asigna al otorgar el turno (US2)
    administrativo_id: str | None = None
    id: str | None = None
