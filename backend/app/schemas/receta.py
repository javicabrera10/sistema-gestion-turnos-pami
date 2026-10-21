from pydantic import BaseModel, Field
from typing import List

class MedicamentoSchema(BaseModel):
    nombre: str
    dosis: str
    horario_toma: str

class RecetaSchema(BaseModel):
    paciente_id: str
    medicamentos: List[MedicamentoSchema]
