from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from .base import BaseRepository


class AvisoTomaRepository(BaseRepository):
    """Registro de los avisos de toma ya creados, para no repetir el mismo aviso."""

    def __init__(self, db):
        super().__init__(db.avisos_toma)

    def registrar(self, receta_id: str, dia: str, medicamento: str, horario: str) -> bool:
        """Anota el aviso. Devuelve False si ya estaba anotado (el índice único impide duplicados)."""
        doc = {
            "receta_id": receta_id,
            "dia": dia,
            "medicamento": medicamento,
            "horario": horario,
            "creado_en": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        try:
            self.insert(doc)
        except DuplicateKeyError:
            return False
        return True
