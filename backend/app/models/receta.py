from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def _ahora() -> datetime:
    # Mongo guarda datetimes en UTC sin zona horaria (igual que en el resto de la app)
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TipoReceta(str, Enum):
    RECETA = "receta"
    ORDEN = "orden"  # estudio o práctica: no lleva medicamentos


class EstadoReceta(str, Enum):
    BORRADOR = "borrador"
    EMITIDA = "emitida"  # ya es visible para el paciente


@dataclass
class Medicamento:
    nombre: str
    dosis: str
    presentacion: str = ""
    horario_toma: str = ""  # texto libre, por ejemplo "Cada 8 horas"


@dataclass
class ItemPlan:
    """Una línea del plan de medicación: qué tomar, cuánto, a qué horas y por cuántos días."""

    medicamento: str
    dosis: str
    horarios: list[str]  # "08:00", "16:00", ...
    duracion_dias: int


@dataclass
class Receta:
    tipo: str
    paciente_id: str
    medico_id: str
    indicaciones: str = ""
    medicamentos: list[Medicamento] = field(default_factory=list)
    plan_medicacion: list[ItemPlan] = field(default_factory=list)
    estado: str = EstadoReceta.BORRADOR.value
    fecha: datetime = field(default_factory=_ahora)
    id: str | None = None
