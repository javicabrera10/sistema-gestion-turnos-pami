from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SolicitudTurnoSchema(BaseModel):
    # extra="forbid": el cliente no puede mandar estado, paciente_id, etc.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    especialidad: str = Field(min_length=3, max_length=60)
    fecha_hora: datetime
    motivo: str = Field(min_length=3, max_length=300)

    @field_validator("fecha_hora")
    @classmethod
    def futura_y_en_utc(cls, v: datetime) -> datetime:
        # Mongo guarda datetimes en UTC sin zona horaria (igual que en AuthService)
        if v.tzinfo is not None:
            v = v.astimezone(timezone.utc).replace(tzinfo=None)
        if v <= datetime.now(timezone.utc).replace(tzinfo=None):
            raise ValueError("La fecha del turno debe ser futura")
        return v
