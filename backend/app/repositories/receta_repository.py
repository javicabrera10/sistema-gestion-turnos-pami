from bson import ObjectId
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
            # una receta con plan de medicación llega al paciente recién cuando el administrativo genera el recordatorio
            filtro["$or"] = [
                {"plan_medicacion": {"$exists": False}},
                {"plan_medicacion": []},
                {"recordatorio_generado_en": {"$ne": None}},
            ]
        return list(self.col.find(filtro).sort("fecha", -1))

    def listar_emitidas(self):
        """Todo lo que los médicos ya emitieron (recetas y órdenes), lo más reciente primero."""
        return list(self.col.find({"estado": EstadoReceta.EMITIDA.value}).sort("fecha", -1))

    def listar_pendientes_de_recordatorio(self):
        """Recetas emitidas con plan de medicación cuyo aviso al paciente todavía no generó el administrativo."""
        filtro = {
            "tipo": TipoReceta.RECETA.value,
            "estado": EstadoReceta.EMITIDA.value,
            "plan_medicacion": {"$exists": True, "$ne": []},
            "recordatorio_generado_en": None,  # también coincide con las recetas que no tienen el campo
        }
        return list(self.col.find(filtro))

    def reclamar_recordatorio(self, id_, cuando) -> bool:
        """Anota que se generó el aviso. Devuelve False si otro administrativo ya lo había generado.

        Es una sola actualización con condición, así que dos administrativos tocando el botón a la vez no duplican el aviso.
        """
        resultado = self.col.update_one(
            {"_id": ObjectId(id_), "recordatorio_generado_en": None}, {"$set": {"recordatorio_generado_en": cuando}}
        )
        return resultado.modified_count == 1

    def actualizar(self, id_, campos: dict) -> None:
        self.update(id_, campos)

    def eliminar(self, id_) -> None:
        self.delete(id_)
