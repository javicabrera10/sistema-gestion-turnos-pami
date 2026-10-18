from pymongo.errors import DuplicateKeyError

from .base import BaseRepository


class EmailDuplicadoError(Exception):
    pass


class UsuarioRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db.usuarios)

    def buscar_por_email(self, email: str):
        return self.col.find_one({"email": email})

    def crear(self, doc: dict) -> str:
        try:
            return self.insert(doc)
        except DuplicateKeyError as e:
            raise EmailDuplicadoError() from e

    def listar(self):
        return list(self.col.find({}, {"password_hash": 0}))

    def registrar_fallo(self, id_, intentos: int, bloqueado_hasta=None):
        self.update(id_, {"intentos_fallidos": intentos, "bloqueado_hasta": bloqueado_hasta})

    def resetear_intentos(self, id_):
        self.update(id_, {"intentos_fallidos": 0, "bloqueado_hasta": None})
