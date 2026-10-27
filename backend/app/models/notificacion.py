from dataclasses import dataclass, field
from datetime import datetime, timezone


def _ahora() -> datetime:
    # Mongo guarda datetimes en UTC sin zona horaria (igual que en el resto de la app)
    return datetime.now(timezone.utc).replace(tzinfo=None)


# Tipos de notificación (campo "tipo"): el frontend elige el ícono según este valor
TIPO_TURNO_OTORGADO = "turno_otorgado"
TIPO_TURNO_REPROGRAMADO = "turno_reprogramado"
TIPO_TURNO_CANCELADO = "turno_cancelado"
TIPO_TURNO_CONFIRMADO = "turno_confirmado"
TIPO_TURNO_RECHAZADO = "turno_rechazado"
TIPO_RECORDATORIO = "recordatorio"
TIPO_TOMA_MEDICACION = "toma_medicacion"


@dataclass
class Notificacion:
    destinatario_id: str
    mensaje: str
    tipo: str = TIPO_TURNO_OTORGADO
    turno_id: str | None = None  # los avisos de turnos lo llevan
    receta_id: str | None = None  # los avisos de toma de medicación lo llevan
    leida: bool = False
    creada_en: datetime = field(default_factory=_ahora)
    id: str | None = None

    def marcar_como_leida(self) -> None:
        self.leida = True
