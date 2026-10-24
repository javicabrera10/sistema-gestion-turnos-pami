from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _ahora() -> datetime:
    # Mongo guarda datetimes en UTC sin zona horaria (igual que en el resto de la app)
    return datetime.now(timezone.utc).replace(tzinfo=None)


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
    origen: str = "manual"  # "manual" o "voz": cómo lo pidió el paciente
    creado_en: datetime = field(default_factory=_ahora)
    id: str | None = None
