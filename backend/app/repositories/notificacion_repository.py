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
        # primero las más nuevas
        return list(self.col.find({"destinatario_id": destinatario_id}).sort("creada_en", -1))

    def marcar_leida(self, id_) -> None:
        self.update(id_, {"leida": True})
