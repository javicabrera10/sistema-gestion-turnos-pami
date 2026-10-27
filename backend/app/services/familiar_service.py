import logging
from dataclasses import asdict

from app.models.familiar import Familiar, MensajeFamiliar
from app.patterns.canal_strategy import CANALES, canal_por_nombre
from app.patterns.observer import (
    TURNO_CANCELADO,
    TURNO_CONFIRMADO,
    TURNO_OTORGADO,
    TURNO_RECORDATORIO,
    TURNO_REPROGRAMADO,
)

log = logging.getLogger("pami.familiar")

# Eventos de turnos que se le avisan al familiar. No se incluyen los rechazos ni nada de recetas o medicación.
EVENTOS_PARA_FAMILIAR = (TURNO_OTORGADO, TURNO_REPROGRAMADO, TURNO_CANCELADO, TURNO_CONFIRMADO, TURNO_RECORDATORIO)

# Datos mínimos: solo quién (nombre de pila), qué (un turno médico) y cuándo. Nunca especialidad, motivo ni datos clínicos.
TEXTOS = {
    TURNO_OTORGADO: "{nombre} tiene un turno médico otorgado para el {cuando}.",
    TURNO_REPROGRAMADO: "El turno médico de {nombre} fue reprogramado para el {cuando}.",
    TURNO_CANCELADO: "El turno médico de {nombre} del {cuando} fue cancelado.",
    TURNO_CONFIRMADO: "{nombre} confirmó su turno médico del {cuando}.",
    TURNO_RECORDATORIO: "Recordatorio: {nombre} tiene un turno médico el {cuando}.",
}


def texto_para_familiar(evento: str, nombre_paciente: str | None, fecha) -> str:
    """Arma el mensaje del familiar con los datos mínimos (nombre de pila, y fecha y hora)."""
    nombre = nombre_paciente.split()[0] if nombre_paciente and nombre_paciente.strip() else "Tu familiar"
    return TEXTOS[evento].format(nombre=nombre, cuando=f"{fecha:%d/%m/%Y} a las {fecha:%H:%M} hs")


class FamiliarService:
    """El paciente administra a quién se le avisa de sus turnos. Solo trabaja con el familiar del propio paciente."""

    def __init__(self, familiares_repo, mensajes_repo, canales=None):
        self.familiares = familiares_repo
        self.mensajes = mensajes_repo
        self.canales = CANALES if canales is None else canales  # Strategy: los canales se pueden cambiar

    def obtener(self, paciente_id: str) -> dict | None:
        return self.familiares.obtener_por_paciente(paciente_id)

    def guardar(self, paciente_id: str, datos) -> dict:
        """Autoriza a un familiar (o reemplaza al anterior). El consentimiento ya lo validó el schema."""
        familiar = Familiar(
            paciente_id=paciente_id,
            nombre=datos.nombre,
            parentesco=datos.parentesco,
            canal=datos.canal,
            contacto=datos.contacto,
        )
        doc = asdict(familiar)
        doc.pop("id")
        self.familiares.guardar(paciente_id, doc)
        # el log no lleva el nombre ni el contacto del familiar: son datos personales de un tercero
        log.info("familiar autorizado paciente=%s canal=%s", paciente_id, datos.canal)
        return self.familiares.obtener_por_paciente(paciente_id)

    def revocar(self, paciente_id: str) -> bool:
        """El paciente quita la autorización: desde ese momento no se le envía nada al familiar."""
        quitado = self.familiares.eliminar_por_paciente(paciente_id)
        log.info("autorización de familiar revocada paciente=%s quitado=%s", paciente_id, quitado)
        return quitado

    def avisar_turno(self, evento: str, datos: dict, nombre_paciente: str | None) -> dict | None:
        """Le avisa al familiar (si hay uno autorizado) lo que pasó con un turno del paciente.

        Devuelve el aviso que quedó en la bandeja de salida, o None si no había familiar autorizado.
        """
        familiar = self.familiares.obtener_por_paciente(datos["paciente_id"])
        if familiar is None:
            return None
        texto = texto_para_familiar(evento, nombre_paciente, datos["fecha_hora"])
        # Strategy: el canal que eligió el paciente arma el mensaje; el servicio no sabe cuál es
        entrega = canal_por_nombre(familiar["canal"], self.canales).enviar(familiar, texto)
        aviso = MensajeFamiliar(
            paciente_id=datos["paciente_id"],
            canal=entrega["canal"],
            destino=entrega["destino"],
            texto=entrega["texto"],
            evento=evento,
            asunto=entrega["asunto"],
        )
        doc = asdict(aviso)
        doc.pop("id")
        self.mensajes.crear(doc)
        # el log no lleva el destino ni el texto: son datos personales
        log.info("aviso al familiar paciente=%s canal=%s evento=%s", datos["paciente_id"], entrega["canal"], evento)
        return doc

    def listar_avisos(self, paciente_id: str) -> list[dict]:
        """Lo que se le envió al familiar, para que el paciente vea exactamente qué se compartió."""
        return self.mensajes.listar_por_paciente(paciente_id)
