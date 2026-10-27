import logging
from dataclasses import asdict

from app.models.familiar import Familiar

log = logging.getLogger("pami.familiar")


class FamiliarService:
    """El paciente administra a quién se le avisa de sus turnos. Solo trabaja con el familiar del propio paciente."""

    def __init__(self, familiares_repo, mensajes_repo):
        self.familiares = familiares_repo
        self.mensajes = mensajes_repo

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

    def listar_avisos(self, paciente_id: str) -> list[dict]:
        """Lo que se le envió al familiar, para que el paciente vea exactamente qué se compartió."""
        return self.mensajes.listar_por_paciente(paciente_id)
