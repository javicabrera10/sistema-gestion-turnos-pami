from dataclasses import dataclass, field
from datetime import datetime
from typing import List

@dataclass
class Medicamento:
    nombre: str
    dosis: str
    horario_toma: str
    id: str | None = None

@dataclass
class Receta:
    paciente_id: str
    medico_id: str
    medicamentos: List[Medicamento] = field(default_factory=list)
    estado: str = "BORRADOR" # BORRADOR, EMITIDA
    fecha_creacion: datetime = field(default_factory=datetime.utcnow)
    id: str | None = None
