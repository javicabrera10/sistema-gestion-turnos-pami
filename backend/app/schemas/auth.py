from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _max_72_bytes(v: str) -> str:
    if len(v.encode("utf-8")) > 72:
        raise ValueError("La contraseña es demasiado larga")
    return v


class RegistroPacienteSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nombre: str = Field(min_length=2, max_length=80)
    email: EmailStr
    telefono: str = Field(min_length=6, max_length=20)
    dni: str = Field(pattern=r"^\d{7,8}$")
    password: str = Field(min_length=8)

    _pw = field_validator("password")(_max_72_bytes)

    @field_validator("email")
    @classmethod
    def email_minuscula(cls, v):
        return v.lower()


class LoginSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(min_length=1)

    _pw = field_validator("password")(_max_72_bytes)

    @field_validator("email")
    @classmethod
    def email_minuscula(cls, v):
        return v.lower()
