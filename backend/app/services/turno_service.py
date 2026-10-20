import logging
from dataclasses import asdict

from app.models.turno import Turno
from app.patterns.turno_state import estado_de

log = logging.getLogger("pami.turnos")


class TurnoNoEncontrado(Exception):
    pass


class TurnoService:
    def __init__(self, turnos_repo):
        self.repo = turnos_repo

    def solicitar(self, paciente_id: str, datos) -> dict:
        turno = Turno(
            paciente_id=paciente_id,
            especialidad=datos.especialidad,
            fecha_hora=datos.fecha_hora,
            motivo=datos.motivo,
        )
        doc = asdict(turno)
        doc.pop("id")
        doc["estado"] = turno.estado.value  # se guarda el texto, no el Enum
        id_ = self.repo.crear(doc)
        log.info("turno solicitado id=%s paciente=%s", id_, paciente_id)
        return self.repo.get_by_id(id_)

    def listar_del_paciente(self, paciente_id: str) -> list[dict]:
        return self.repo.listar_por_paciente(paciente_id)

    def confirmar(self, turno_id: str, paciente_id: str) -> dict:
        turno = self._turno_del_paciente(turno_id, paciente_id)
        return self._cambiar_estado(turno, estado_de(turno["estado"]).confirmar())

    def rechazar(self, turno_id: str, paciente_id: str) -> dict:
        turno = self._turno_del_paciente(turno_id, paciente_id)
        return self._cambiar_estado(turno, estado_de(turno["estado"]).rechazar())

    def _turno_del_paciente(self, turno_id: str, paciente_id: str) -> dict:
        turno = self.repo.get_by_id(turno_id)
        # Si el turno es de otro paciente se responde igual que si no existiera
        if turno is None or turno["paciente_id"] != paciente_id:
            log.warning("turno inexistente o ajeno id=%s paciente=%s", turno_id, paciente_id)
            raise TurnoNoEncontrado()
        return turno

    def _cambiar_estado(self, turno: dict, nuevo) -> dict:
        self.repo.actualizar_estado(turno["_id"], nuevo)
        log.info("turno id=%s paso a %s", turno["_id"], nuevo.value)
        return self.repo.get_by_id(turno["_id"])
