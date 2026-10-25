from dataclasses import dataclass, field
from datetime import datetime

# Preferencias de accesibilidad con las que arranca cada usuario
PREFERENCIAS_POR_DEFECTO = {
    "tamano_letra": "normal",  # normal | grande | muy_grande
    "alto_contraste": False,
    "voz_activada": True,
}


def preferencias_por_defecto() -> dict:
    return dict(PREFERENCIAS_POR_DEFECTO)


@dataclass
class Usuario:
    nombre: str
    email: str
    telefono: str
    password_hash: str = ""
    id: str | None = None
    intentos_fallidos: int = 0
    bloqueado_hasta: datetime | None = None
    rol: str = field(init=False, default="")
    preferencias: dict = field(init=False, default_factory=preferencias_por_defecto)

    def actualizar_datos(self, **datos):
        for k, v in datos.items():
            if k in ("nombre", "telefono", "email"):
                setattr(self, k, v)


@dataclass
class Paciente(Usuario):
    dni: str = ""
    historia_clinica: str = ""

    def __post_init__(self):
        self.rol = "paciente"


@dataclass
class Medico(Usuario):
    matricula: str = ""
    especialidad: str = ""

    def __post_init__(self):
        self.rol = "medico"


@dataclass
class Administrativo(Usuario):
    legajo: str = ""

    def __post_init__(self):
        self.rol = "administrativo"
