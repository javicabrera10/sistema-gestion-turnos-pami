from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.turno import EstadoTurno

ID_MONGO = r"^[0-9a-fA-F]{24}$"


def _futura_y_en_utc(v: datetime) -> datetime:
    # Mongo guarda datetimes en UTC sin zona horaria (igual que en AuthService)
    if v.tzinfo is not None:
        v = v.astimezone(timezone.utc).replace(tzinfo=None)
    if v <= datetime.now(timezone.utc).replace(tzinfo=None):
        raise ValueError("La fecha del turno debe ser futura")
    return v


class SolicitudTurnoSchema(BaseModel):
    # extra="forbid": el cliente no puede mandar estado, paciente_id, etc.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    especialidad: str = Field(min_length=3, max_length=60)
    fecha_hora: datetime
    motivo: str = Field(min_length=3, max_length=300)
    # cómo lo pidió el paciente: el frontend manda "voz" cuando usó el reconocimiento de voz
    origen: Literal["manual", "voz"] = "manual"

    _fecha = field_validator("fecha_hora")(_futura_y_en_utc)


class RespuestaTurnoSchema(BaseModel):
    """Respuesta del paciente a un turno otorgado: botón Aceptar o Rechazar."""

    model_config = ConfigDict(extra="forbid")

    accion: Literal["aceptar", "rechazar"]


class OtorgarTurnoSchema(BaseModel):
    """Lo que manda el administrativo al otorgar: médico y fecha/hora confirmadas."""

    model_config = ConfigDict(extra="forbid")

    medico_id: str = Field(pattern=ID_MONGO)
    fecha_hora: datetime

    _fecha = field_validator("fecha_hora")(_futura_y_en_utc)


class FiltroTurnosSchema(BaseModel):
    """Parámetros de la URL para listar turnos: /api/turnos?estado=solicitado"""

    model_config = ConfigDict(extra="forbid")

    estado: EstadoTurno | None = None


class FiltroMedicosSchema(BaseModel):
    """Parámetros de la URL para listar médicos: /api/medicos?especialidad=Cardiología"""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    especialidad: str | None = Field(default=None, max_length=60)
