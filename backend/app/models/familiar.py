from dataclasses import dataclass, field
from datetime import datetime, timezone

CANAL_SMS = "sms"
CANAL_EMAIL = "email"


def _ahora() -> datetime:
    # Mongo guarda datetimes en UTC sin zona horaria (igual que en el resto de la app)
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class Familiar:
    """Persona que el paciente autorizó a recibir avisos de sus turnos. No es usuario del sistema."""

    paciente_id: str
    nombre: str
    parentesco: str
    canal: str  # "sms" o "email"
    contacto: str  # teléfono o email, según el canal
    autorizado_en: datetime = field(default_factory=_ahora)
    id: str | None = None


@dataclass
class MensajeFamiliar:
    """Un aviso que el sistema le mandó (de forma simulada) al familiar: queda en la bandeja de salida."""

    paciente_id: str
    canal: str
    destino: str
    texto: str
    evento: str  # qué lo originó, por ejemplo "turno.otorgado"
    asunto: str = ""  # solo los emails llevan asunto
    estado: str = "enviado (simulado)"
    creado_en: datetime = field(default_factory=_ahora)
    id: str | None = None
