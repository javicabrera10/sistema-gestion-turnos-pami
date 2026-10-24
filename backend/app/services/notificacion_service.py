import logging
from dataclasses import asdict

from app.models.notificacion import Notificacion

log = logging.getLogger("pami.notificaciones")


class NotificacionNoEncontrada(Exception):
    pass


class NotificacionService:
    def __init__(self, repo):
        self.repo = repo

    def crear_turno_otorgado(self, datos: dict) -> str:
        """Avisa al paciente que le otorgaron el turno, con fecha y hora (observer de turno.otorgado)."""
        fecha = datos["fecha_hora"]
        especialidad = datos.get("especialidad")
        de = f" de {especialidad}" if especialidad else ""
        mensaje = f"Te otorgaron un turno{de} para el {fecha:%d/%m/%Y} a las {fecha:%H:%M} hs."
        doc = asdict(
            Notificacion(destinatario_id=datos["paciente_id"], turno_id=datos["turno_id"], mensaje=mensaje)
        )
        doc.pop("id")
        id_ = self.repo.crear(doc)
        log.info("notificación creada id=%s destinatario=%s", id_, datos["paciente_id"])
        return id_

    def listar_mias(self, destinatario_id: str) -> list[dict]:
        return self.repo.listar_por_destinatario(destinatario_id)

    def marcar_leida(self, notificacion_id: str, destinatario_id: str) -> dict:
        notif = self.repo.get_by_id(notificacion_id)
        # Si es de otra persona se responde igual que si no existiera
        if notif is None or notif["destinatario_id"] != destinatario_id:
            raise NotificacionNoEncontrada()
        self.repo.marcar_leida(notif["_id"])
        return self.repo.get_by_id(notif["_id"])
