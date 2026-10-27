import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StrictBool,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)

_EMAIL = TypeAdapter(EmailStr)
_TELEFONO = re.compile(r"^\+?\d{8,15}$")


class FamiliarSchema(BaseModel):
    """Lo que manda el paciente para autorizar a un familiar. Sin consentimiento no se guarda nada."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    nombre: str = Field(min_length=2, max_length=80)
    parentesco: str = Field(min_length=2, max_length=40)
    canal: Literal["sms", "email"]
    contacto: str = Field(min_length=5, max_length=120)
    consentimiento: StrictBool  # solo el booleano true: "true" o 1 no cuentan como consentimiento

    @field_validator("consentimiento")
    @classmethod
    def _exigir_consentimiento(cls, v):
        if v is not True:
            raise ValueError("Hace falta que el paciente autorice que se le avise a este familiar")
        return v

    @model_validator(mode="after")
    def _contacto_segun_el_canal(self):
        if self.canal == "email":
            try:
                self.contacto = _EMAIL.validate_python(self.contacto).lower()
            except ValidationError:
                raise ValueError("El email del familiar no es válido") from None
        else:
            telefono = re.sub(r"[\s\-().]", "", self.contacto)
            if not _TELEFONO.match(telefono):
                raise ValueError("El teléfono del familiar no es válido (solo números, de 8 a 15 dígitos)")
            self.contacto = telefono
        return self
