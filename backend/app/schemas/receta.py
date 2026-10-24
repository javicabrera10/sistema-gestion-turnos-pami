import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ID_MONGO = r"^[0-9a-fA-F]{24}$"
HORA = r"^([01]\d|2[0-3]):[0-5]\d$"


class MedicamentoSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nombre: str = Field(min_length=2, max_length=80)
    dosis: str = Field(min_length=1, max_length=60)
    presentacion: str = Field(default="", max_length=60)
    horario_toma: str = Field(default="", max_length=60)


class ItemPlanSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    medicamento: str = Field(min_length=2, max_length=80)
    dosis: str = Field(min_length=1, max_length=60)
    horarios: list[str] = Field(min_length=1, max_length=12)
    duracion_dias: int = Field(ge=1, le=365)

    @model_validator(mode="after")
    def horarios_validos(self):
        for h in self.horarios:
            if not re.fullmatch(HORA, h):
                raise ValueError(f"Horario inválido: {h!r}. Usá el formato HH:MM, por ejemplo 08:00")
        return self


class RecetaCrearSchema(BaseModel):
    """Alta de una receta (lleva medicamentos) o de una orden (estudio o práctica)."""

    # extra="forbid": el cliente no puede mandar medico_id, estado, fecha, etc.
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    tipo: Literal["receta", "orden"] = "receta"
    paciente_id: str = Field(pattern=ID_MONGO)
    indicaciones: str = Field(default="", max_length=1000)
    medicamentos: list[MedicamentoSchema] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def segun_tipo(self):
        if self.tipo == "receta" and not self.medicamentos:
            raise ValueError("Una receta necesita al menos un medicamento")
        if self.tipo == "orden":
            if self.medicamentos:
                raise ValueError("Una orden no lleva medicamentos: detallá el estudio en las indicaciones")
            if len(self.indicaciones) < 3:
                raise ValueError("Una orden necesita indicar el estudio o la práctica")
        return self


class RecetaEditarSchema(BaseModel):
    """Edición: solo indicaciones y medicamentos. El tipo y el paciente no se pueden cambiar."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    indicaciones: str | None = Field(default=None, max_length=1000)
    medicamentos: list[MedicamentoSchema] | None = Field(default=None, max_length=20)

    @model_validator(mode="after")
    def algo_para_cambiar(self):
        if self.indicaciones is None and self.medicamentos is None:
            raise ValueError("No hay nada para modificar")
        return self


class PlanSchema(BaseModel):
    """Plan de medicación: lista de medicamentos con dosis, horarios y duración."""

    model_config = ConfigDict(extra="forbid")

    plan: list[ItemPlanSchema] = Field(min_length=1, max_length=20)
