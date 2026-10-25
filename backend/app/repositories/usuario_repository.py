from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.models.usuario import PREFERENCIAS_POR_DEFECTO

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

    def buscar_por_ids(self, ids):
        oids = [ObjectId(i) for i in ids]
        return list(self.col.find({"_id": {"$in": oids}}, {"password_hash": 0}))

    def registrar_fallo(self, id_, intentos: int, bloqueado_hasta=None):
        self.update(id_, {"intentos_fallidos": intentos, "bloqueado_hasta": bloqueado_hasta})

    def resetear_intentos(self, id_):
        self.update(id_, {"intentos_fallidos": 0, "bloqueado_hasta": None})

    def listar_por_rol(self, rol: str, especialidad: str | None = None):
        """Usuarios de un rol (sin credenciales). La especialidad se compara sin mayúsculas ni espacios."""
        docs = list(self.col.find({"rol": rol}, {"password_hash": 0}))
        if especialidad:
            buscada = especialidad.strip().lower()
            docs = [d for d in docs if str(d.get("especialidad", "")).strip().lower() == buscada]
        return docs

    def buscar_paciente_por_dni(self, dni: str):
        """Solo id, nombre y DNI: lo mínimo para identificar al paciente."""
        return self.col.find_one({"rol": "paciente", "dni": dni}, {"nombre": 1, "dni": 1})

    def obtener_preferencias(self, id_):
        """Preferencias de accesibilidad (con valores por defecto si todavia no las guardo). None si no existe."""
        doc = self.col.find_one({"_id": ObjectId(id_)}, {"preferencias": 1})
        if doc is None:
            return None
        return {**PREFERENCIAS_POR_DEFECTO, **doc.get("preferencias", {})}

    def guardar_preferencias(self, id_, preferencias: dict):
        self.update(id_, {"preferencias": preferencias})