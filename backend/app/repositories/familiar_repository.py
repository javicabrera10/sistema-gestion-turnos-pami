from .base import BaseRepository


class FamiliarRepository(BaseRepository):
    """Un familiar autorizado por paciente (el índice único de paciente_id lo garantiza)."""

    def __init__(self, db):
        super().__init__(db.familiares_autorizados)

    def obtener_por_paciente(self, paciente_id: str):
        return self.col.find_one({"paciente_id": paciente_id})

    def guardar(self, paciente_id: str, campos: dict) -> None:
        """Crea el familiar del paciente o reemplaza sus datos si ya tenía uno."""
        self.col.update_one({"paciente_id": paciente_id}, {"$set": campos}, upsert=True)

    def eliminar_por_paciente(self, paciente_id: str) -> bool:
        return self.col.delete_one({"paciente_id": paciente_id}).deleted_count > 0


class MensajeFamiliarRepository(BaseRepository):
    """Bandeja de salida: los avisos que el sistema le mandó al familiar de cada paciente."""

    def __init__(self, db):
        super().__init__(db.mensajes_familiar)

    def crear(self, doc: dict) -> str:
        return self.insert(doc)

    def listar_por_paciente(self, paciente_id: str, limite: int = 50):
        # primero los más nuevos; se desempata por _id, que crece en el orden de inserción
        cursor = self.col.find({"paciente_id": paciente_id}).sort([("creado_en", -1), ("_id", -1)])
        return list(cursor.limit(limite))
