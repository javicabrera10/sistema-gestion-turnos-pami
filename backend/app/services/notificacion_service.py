import logging
from dataclasses import asdict

from app.models.notificacion import (
    TIPO_RECETA_EMITIDA,
    TIPO_RECORDATORIO,
    TIPO_TOMA_MEDICACION,
    TIPO_TURNO_CANCELADO,
    TIPO_TURNO_CONFIRMADO,
    TIPO_TURNO_OTORGADO,
    TIPO_TURNO_RECHAZADO,
    TIPO_TURNO_REPROGRAMADO,
    Notificacion,
)

log = logging.getLogger("pami.notificaciones")


class NotificacionNoEncontrada(Exception):
    pass


def _de_especialidad(datos: dict) -> str:
    especialidad = datos.get("especialidad")
    return f" de {especialidad}" if especialidad else ""


def _cuando(fecha) -> str:
    return f"{fecha:%d/%m/%Y} a las {fecha:%H:%M} hs"


class NotificacionService:
    def __init__(self, repo):
        self.repo = repo

    def _crear(self, destinatario_id: str, turno_id: str | None, tipo: str, mensaje: str, receta_id: str | None = None) -> str:
        notificacion = Notificacion(
            destinatario_id=destinatario_id, mensaje=mensaje, tipo=tipo, turno_id=turno_id, receta_id=receta_id
        )
        # solo se guardan los campos que tienen valor: un aviso de turno no lleva receta_id y uno de toma no lleva turno_id
        doc = {k: v for k, v in asdict(notificacion).items() if v is not None}
        id_ = self.repo.crear(doc)
        # el mensaje no se loguea: puede incluir el nombre del paciente
        log.info("notificación creada id=%s tipo=%s destinatario=%s", id_, tipo, destinatario_id)
        return id_

    def crear_turno_otorgado(self, datos: dict) -> str:
        """Avisa al paciente que le otorgaron el turno, con fecha y hora (observer de turno.otorgado)."""
        mensaje = f"Te otorgaron un turno{_de_especialidad(datos)} para el {_cuando(datos['fecha_hora'])}."
        return self._crear(datos["paciente_id"], datos["turno_id"], TIPO_TURNO_OTORGADO, mensaje)

    def crear_turno_reprogramado(self, datos: dict) -> str:
        """Avisa al paciente la nueva fecha y le pide que la acepte o la rechace (observer de turno.reprogramado)."""
        mensaje = (
            f"Reprogramaron tu turno{_de_especialidad(datos)}. Nueva fecha: {_cuando(datos['fecha_hora'])}. "
            "Entrá a Mis turnos para aceptarlo o rechazarlo."
        )
        return self._crear(datos["paciente_id"], datos["turno_id"], TIPO_TURNO_REPROGRAMADO, mensaje)

    def crear_turno_cancelado(self, datos: dict) -> str:
        """Avisa al paciente que cancelaron su turno (observer de turno.cancelado)."""
        mensaje = f"Cancelaron tu turno{_de_especialidad(datos)} del {_cuando(datos['fecha_hora'])}."
        return self._crear(datos["paciente_id"], datos["turno_id"], TIPO_TURNO_CANCELADO, mensaje)

    def crear_respuesta_paciente(self, datos: dict, aceptado: bool, paciente_nombre: str | None = None) -> str | None:
        """Avisa al administrativo que otorgó el turno si el paciente lo aceptó o lo rechazó."""
        administrativo_id = datos.get("administrativo_id")
        if not administrativo_id:
            return None  # turno sin administrativo asignado: no hay a quién avisar
        quien = paciente_nombre or "El paciente"
        accion, tipo = ("confirmó", TIPO_TURNO_CONFIRMADO) if aceptado else ("rechazó", TIPO_TURNO_RECHAZADO)
        mensaje = f"{quien} {accion} el turno{_de_especialidad(datos)} del {_cuando(datos['fecha_hora'])}."
        return self._crear(administrativo_id, datos["turno_id"], tipo, mensaje)

    def crear_recordatorio(self, datos: dict) -> str:
        """Le recuerda al paciente que se acerca su turno (lo genera el servicio de recordatorios)."""
        mensaje = f"Recordatorio: tenés un turno{_de_especialidad(datos)} el {_cuando(datos['fecha_hora'])}."
        return self._crear(datos["paciente_id"], datos["turno_id"], TIPO_RECORDATORIO, mensaje)

    def crear_toma_medicacion(self, datos: dict) -> str:
        """Le entrega al paciente su receta con el plan de toma (la genera el servicio de tomas cuando el administrativo toca el botón)."""
        lineas = []
        for item in datos["plan"]:
            dias = item["duracion_dias"]
            horarios = ", ".join(item["horarios"])
            lineas.append(f"{item['medicamento']} ({item['dosis']}) a las {horarios} hs durante {dias} {'día' if dias == 1 else 'días'}")
        mensaje = f"Tu médico te emitió una receta. Plan de toma: {'; '.join(lineas)}."
        if datos.get("indicaciones"):
            mensaje += f" Indicaciones: {datos['indicaciones']}"
        return self._crear(datos["paciente_id"], None, TIPO_TOMA_MEDICACION, mensaje, receta_id=datos["receta_id"])

    def crear_receta_emitida(self, administrativo_id: str, datos: dict, medico_nombre: str | None = None, paciente_nombre: str | None = None) -> str:
        """Le avisa a un administrativo que el médico emitió una receta con plan de medicación (observer de receta.emitida).

        No lleva medicamentos ni dosis: son datos de salud y al administrativo le alcanza con saber de qué paciente se trata.
        """
        quien = medico_nombre or "Un médico"
        para = paciente_nombre or "un paciente"
        mensaje = (
            f"{quien} emitió una receta con plan de medicación para {para}. "
            "Tocá «Generar recordatorios» para que el paciente reciba su receta y el aviso de toma."
        )
        return self._crear(administrativo_id, None, TIPO_RECETA_EMITIDA, mensaje, receta_id=datos["receta_id"])

    def resolver_receta_emitida(self, receta_id: str) -> None:
        """Ya se generó el recordatorio de esa receta: el aviso pendiente de los administrativos se marca como leído."""
        self.repo.marcar_leidas_de_receta(receta_id, TIPO_RECETA_EMITIDA)

    def listar_mias(self, destinatario_id: str) -> list[dict]:
        return self.repo.listar_por_destinatario(destinatario_id)

    def marcar_leida(self, notificacion_id: str, destinatario_id: str) -> dict:
        notif = self.repo.get_by_id(notificacion_id)
        # Si es de otra persona se responde igual que si no existiera
        if notif is None or notif["destinatario_id"] != destinatario_id:
            raise NotificacionNoEncontrada()
        self.repo.marcar_leida(notif["_id"])
        return self.repo.get_by_id(notif["_id"])
