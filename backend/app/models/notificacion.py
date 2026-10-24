from dataclasses import dataclass, field
from datetime import datetime, timezone


def _ahora() -> datetime:
    # Mongo guarda datetimes en UTC sin zona horaria (igual que en el resto de la app)
    return datetime.now(timezone.utc).replace(tzinfo=None)


@dataclass
class Notificacion:
    destinatario_id: str
    turno_id: str
    mensaje: str
    tipo: str = "turno_otorgado"
    leida: bool = False
    creada_en: datetime = field(default_factory=_ahora)
    id: str | None = None

    def marcar_como_leida(self) -> None:
        self.leida = True
