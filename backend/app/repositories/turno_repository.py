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
