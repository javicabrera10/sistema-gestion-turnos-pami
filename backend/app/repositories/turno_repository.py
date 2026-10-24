from bson import ObjectId
from bson.errors import InvalidId

from app.models.turno import EstadoTurno

from .base import BaseRepository


class TurnoRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db.turnos)

    def get_by_id(self, id_):
        # Un id mal formado en la URL no es un error del servidor: simplemente no existe
        try:
            return super().get_by_id(id_)
        except InvalidId:
            return None

    def crear(self, doc: dict) -> str:
        return self.insert(doc)

    def listar_por_paciente(self, paciente_id: str):
        return list(self.col.find({"paciente_id": paciente_id}).sort("fecha_hora", 1))

    def actualizar_estado(self, id_, estado: EstadoTurno):
        self.update(id_, {"estado": estado.value})

    def listar(self, estado: EstadoTurno | None = None):
        filtro = {"estado": estado.value} if estado else {}
        return list(self.col.find(filtro).sort("fecha_hora", 1))

    def registrar_otorgamiento(self, id_, medico_id, fecha_hora, administrativo_id, estado: EstadoTurno):
        self.update(
            id_,
            {
                "medico_id": medico_id,
                "fecha_hora": fecha_hora,
                "administrativo_id": administrativo_id,
                "estado": estado.value,
            },
        )

    def registrar_reprogramacion(self, id_, fecha_hora, administrativo_id, estado: EstadoTurno):
        self.update(
            id_,
            {
                "fecha_hora": fecha_hora,
                "administrativo_id": administrativo_id,
                "estado": estado.value,
                # con otra fecha, los recordatorios vuelven a empezar
                "recordatorios_enviados": [],
            },
        )

    def listar_confirmados_entre(self, desde, hasta):
        """Turnos confirmados que son después de `desde` y hasta `hasta` (inclusive), del más próximo al más lejano."""
        filtro = {"estado": EstadoTurno.CONFIRMADO.value, "fecha_hora": {"$gt": desde, "$lte": hasta}}
        return list(self.col.find(filtro).sort("fecha_hora", 1))

    def marcar_recordatorios_enviados(self, id_, nombres) -> None:
        """Anota qué reglas de recordatorio ya se cumplieron para este turno (sin repetir nombres)."""
        self.col.update_one({"_id": ObjectId(id_)}, {"$addToSet": {"recordatorios_enviados": {"$each": list(nombres)}}})

    def horario_ocupado(self, medico_id: str, fecha_hora, excluir_id=None) -> bool:
        """True si el médico ya tiene otro turno otorgado, reprogramado o confirmado a esa fecha y hora."""
        ocupados = self.col.find(
            {
                "medico_id": medico_id,
                "fecha_hora": fecha_hora,
                "estado": {
                    "$in": [EstadoTurno.OTORGADO.value, EstadoTurno.REPROGRAMADO.value, EstadoTurno.CONFIRMADO.value]
                },
            }
        )
        return any(str(t["_id"]) != str(excluir_id) for t in ocupados)
