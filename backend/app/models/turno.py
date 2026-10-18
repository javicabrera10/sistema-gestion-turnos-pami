from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EstadoTurno(str, Enum):
    SOLICITADO = "solicitado"
    CONFIRMADO = "confirmado"
    RECHAZADO = "rechazado"
    REPROGRAMADO = "reprogramado"
    CANCELADO = "cancelado"


@dataclass
class Turno:
    paciente_id: str
    medico_id: str
    fecha_hora: datetime
    motivo: str
    estado: EstadoTurno = EstadoTurno.SOLICITADO
    administrativo_id: str | None = None
    id: str | None = None
