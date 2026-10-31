from bson.errors import InvalidId

from .base import BaseRepository


class NotificacionRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db.notificaciones)

    def get_by_id(self, id_):
        # Un id mal formado en la URL no es un error del servidor: simplemente no existe
        try:
            return super().get_by_id(id_)
        except InvalidId:
            return None

    def crear(self, doc: dict) -> str:
        return self.insert(doc)

    def listar_por_destinatario(self, destinatario_id: str):
        # primero las más nuevas. El reloj puede dar la misma fecha a dos avisos creados casi juntos
        # (en Windows tiene ~15 ms de resolución y Mongo guarda milisegundos), así que se desempata
        # por _id, que crece en el orden de inserción.
        return list(self.col.find({"destinatario_id": destinatario_id}).sort([("creada_en", -1), ("_id", -1)]))

    def marcar_leida(self, id_) -> None:
        self.update(id_, {"leida": True})

    def marcar_leidas_de_receta(self, receta_id: str, tipo: str) -> None:
        """Marca como leídos los avisos de un tipo que hablan de una receta (de todos los destinatarios)."""
        self.col.update_many({"receta_id": receta_id, "tipo": tipo, "leida": False}, {"$set": {"leida": True}})
