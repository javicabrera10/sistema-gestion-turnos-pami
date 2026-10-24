import logging

from app.patterns.observer import TURNO_CANCELADO, TURNO_OTORGADO, TURNO_REPROGRAMADO
from app.patterns.turno_state import estado_de
from app.services.turno_service import TurnoNoEncontrado, datos_evento

log = logging.getLogger("pami.turnos")


class MedicoInvalido(Exception):
    pass


class HorarioOcupado(Exception):
    pass


class TurnoAdminService:
    """Operaciones del administrativo sobre los turnos (ver solicitudes, otorgar, reprogramar y cancelar)."""

    def __init__(self, turnos_repo, usuarios_repo, event_bus=None):
        self.turnos = turnos_repo
        self.usuarios = usuarios_repo
        self.bus = event_bus

    def listar(self, estado=None) -> list[dict]:
        return self._con_pacientes(self.turnos.listar(estado))

    def obtener(self, turno_id: str) -> dict:
        turno = self.turnos.get_by_id(turno_id)
        if turno is None:
            raise TurnoNoEncontrado()
        return self._con_pacientes([turno])[0]

    def otorgar(self, turno_id: str, administrativo_id: str, datos) -> dict:
        turno = self.turnos.get_by_id(turno_id)
        if turno is None:
            raise TurnoNoEncontrado()

        # Patrón State: lanza TransicionInvalida si el turno no está solicitado
        nuevo_estado = estado_de(turno["estado"]).otorgar()

        medico = self.usuarios.get_by_id(datos.medico_id)
        if medico is None or medico.get("rol") != "medico":
            raise MedicoInvalido()

        if self.turnos.horario_ocupado(datos.medico_id, datos.fecha_hora, excluir_id=turno["_id"]):
            raise HorarioOcupado()

        self.turnos.registrar_otorgamiento(
            turno["_id"], datos.medico_id, datos.fecha_hora, administrativo_id, nuevo_estado
        )
        log.info(
            "turno id=%s otorgado por administrativo=%s medico=%s",
            turno["_id"], administrativo_id, datos.medico_id,
        )
        otorgado = self.turnos.get_by_id(turno["_id"])
        if self.bus is not None:
            # el observer de notificaciones le avisa al paciente con la fecha y hora
            self.bus.publicar(TURNO_OTORGADO, datos_evento(otorgado))
        return self.obtener(turno_id)

    def reprogramar(self, turno_id: str, administrativo_id: str, datos) -> dict:
        turno = self.turnos.get_by_id(turno_id)
        if turno is None:
            raise TurnoNoEncontrado()

        # Patrón State: solo se reprograma un turno otorgado, confirmado o ya reprogramado
        nuevo_estado = estado_de(turno["estado"]).reprogramar()

        medico_id = turno.get("medico_id")
        if medico_id and self.turnos.horario_ocupado(medico_id, datos.fecha_hora, excluir_id=turno["_id"]):
            raise HorarioOcupado()

        self.turnos.registrar_reprogramacion(turno["_id"], datos.fecha_hora, administrativo_id, nuevo_estado)
        log.info("turno id=%s reprogramado por administrativo=%s", turno["_id"], administrativo_id)
        self._publicar(TURNO_REPROGRAMADO, turno["_id"])
        return self.obtener(turno_id)

    def cancelar(self, turno_id: str, administrativo_id: str) -> dict:
        turno = self.turnos.get_by_id(turno_id)
        if turno is None:
            raise TurnoNoEncontrado()

        # Patrón State: solo se cancela un turno otorgado, confirmado o reprogramado
        nuevo_estado = estado_de(turno["estado"]).cancelar()

        self.turnos.actualizar_estado(turno["_id"], nuevo_estado)
        log.info("turno id=%s cancelado por administrativo=%s", turno["_id"], administrativo_id)
        self._publicar(TURNO_CANCELADO, turno["_id"])
        return self.obtener(turno_id)

    def _publicar(self, evento: str, turno_id) -> None:
        if self.bus is not None:
            # el observer de notificaciones le avisa al paciente
            self.bus.publicar(evento, datos_evento(self.turnos.get_by_id(turno_id)))

    def _con_pacientes(self, turnos: list[dict]) -> list[dict]:
        ids = list({t["paciente_id"] for t in turnos})
        pacientes = {str(p["_id"]): p for p in self.usuarios.buscar_por_ids(ids)} if ids else {}
        return [{**t, "paciente": pacientes.get(t["paciente_id"])} for t in turnos]
