from bson.errors import InvalidId

from app.models.receta import EstadoReceta, TipoReceta

from .base import BaseRepository


class RecetaRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db.recetas)

    def get_by_id(self, id_):
        # Un id mal formado en la URL no es un error del servidor: simplemente no existe
        try:
            return super().get_by_id(id_)
        except InvalidId:
            return None

    def crear(self, doc: dict) -> str:
        return self.insert(doc)

    def listar_por_medico(self, medico_id: str):
        return list(self.col.find({"medico_id": medico_id}).sort("fecha", -1))

    def listar_por_paciente(self, paciente_id: str, solo_emitidas: bool = True):
        filtro = {"paciente_id": paciente_id}
        if solo_emitidas:
            filtro["estado"] = EstadoReceta.EMITIDA.value
        return list(self.col.find(filtro).sort("fecha", -1))

    def listar_con_plan_activo(self):
        """Recetas emitidas con plan de medicación cargado y con inicio (lo que necesita el aviso de toma)."""
        filtro = {
            "tipo": TipoReceta.RECETA.value,
            "estado": EstadoReceta.EMITIDA.value,
            "plan_medicacion": {"$exists": True, "$ne": []},
            "inicio_plan": {"$ne": None},
        }
        return list(self.col.find(filtro))

    def actualizar(self, id_, campos: dict) -> None:
        self.update(id_, campos)

    def eliminar(self, id_) -> None:
        self.delete(id_)
