import logging
from dataclasses import asdict

from app.models.turno import Turno
from app.patterns.observer import TURNO_CONFIRMADO, TURNO_RECHAZADO, TURNO_SOLICITADO
from app.patterns.turno_state import estado_de

log = logging.getLogger("pami.turnos")


class TurnoNoEncontrado(Exception):
    pass


def datos_evento(turno: dict) -> dict:
    """Lo que se publica en el bus de eventos (contrato del Sprint 1 + la especialidad)."""
    return {
        "turno_id": str(turno["_id"]),
        "paciente_id": turno["paciente_id"],
        "medico_id": turno.get("medico_id"),
        "especialidad": turno.get("especialidad"),
        "fecha_hora": turno["fecha_hora"],
    }


class TurnoService:
    def __init__(self, turnos_repo, event_bus=None):
        self.repo = turnos_repo
        self.bus = event_bus  # opcional: sin bus el servicio funciona igual, solo no avisa a nadie

    def solicitar(self, paciente_id: str, datos) -> dict:
        turno = Turno(
            paciente_id=paciente_id,
            especialidad=datos.especialidad,
            fecha_hora=datos.fecha_hora,
            motivo=datos.motivo,
            origen=getattr(datos, "origen", "manual"),
        )
        doc = asdict(turno)
        doc.pop("id")
        doc["estado"] = turno.estado.value  # se guarda el texto, no el Enum
        id_ = self.repo.crear(doc)
        log.info("turno solicitado id=%s paciente=%s origen=%s", id_, paciente_id, turno.origen)
        creado = self.repo.get_by_id(id_)
        self._publicar(TURNO_SOLICITADO, creado)
        return creado

    def listar_del_paciente(self, paciente_id: str) -> list[dict]:
        return self.repo.listar_por_paciente(paciente_id)

    listar_mios = listar_del_paciente  # nombre del contrato del Sprint 1

    def confirmar(self, turno_id: str, paciente_id: str) -> dict:
        turno = self._turno_del_paciente(turno_id, paciente_id)
        return self._cambiar_estado(turno, estado_de(turno["estado"]).confirmar(), TURNO_CONFIRMADO)

    def rechazar(self, turno_id: str, paciente_id: str) -> dict:
        turno = self._turno_del_paciente(turno_id, paciente_id)
        return self._cambiar_estado(turno, estado_de(turno["estado"]).rechazar(), TURNO_RECHAZADO)

    def _turno_del_paciente(self, turno_id: str, paciente_id: str) -> dict:
        turno = self.repo.get_by_id(turno_id)
        # Si el turno es de otro paciente se responde igual que si no existiera
        if turno is None or turno["paciente_id"] != paciente_id:
            log.warning("turno inexistente o ajeno id=%s paciente=%s", turno_id, paciente_id)
            raise TurnoNoEncontrado()
        return turno

    def _cambiar_estado(self, turno: dict, nuevo, evento: str) -> dict:
        self.repo.actualizar_estado(turno["_id"], nuevo)
        log.info("turno id=%s paso a %s", turno["_id"], nuevo.value)
        actualizado = self.repo.get_by_id(turno["_id"])
        self._publicar(evento, actualizado)
        return actualizado

    def _publicar(self, evento: str, turno: dict) -> None:
        if self.bus is not None:
            self.bus.publicar(evento, datos_evento(turno))
