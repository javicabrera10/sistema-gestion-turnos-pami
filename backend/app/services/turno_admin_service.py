import logging

from app.patterns.turno_state import estado_de
from app.services.turno_service import TurnoNoEncontrado

log = logging.getLogger("pami.turnos")


class MedicoInvalido(Exception):
    pass


class TurnoAdminService:
    """Operaciones del administrativo sobre los turnos (ver solicitudes y otorgar)."""

    def __init__(self, turnos_repo, usuarios_repo):
        self.turnos = turnos_repo
        self.usuarios = usuarios_repo

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

        self.turnos.registrar_otorgamiento(
            turno["_id"], datos.medico_id, datos.fecha_hora, administrativo_id, nuevo_estado
        )
        log.info(
            "turno id=%s otorgado por administrativo=%s medico=%s",
            turno["_id"], administrativo_id, datos.medico_id,
        )
        return self.obtener(turno_id)

    def _con_pacientes(self, turnos: list[dict]) -> list[dict]:
        ids = list({t["paciente_id"] for t in turnos})
        pacientes = {str(p["_id"]): p for p in self.usuarios.buscar_por_ids(ids)} if ids else {}
        return [{**t, "paciente": pacientes.get(t["paciente_id"])} for t in turnos]
