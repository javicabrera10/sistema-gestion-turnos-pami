from bson import ObjectId
from app.models.receta import Receta, Medicamento
from dataclasses import asdict

class RecetaRepository:
    def __init__(self, db):
        self.collection = db.recetas

    def crear(self, receta: Receta) -> str:
        data = asdict(receta)
        if 'id' in data: del data['id']
        res = self.collection.insert_one(data)
        return str(res.inserted_id)

    def get_by_id(self, receta_id: str):
        data = self.collection.find_one({"_id": ObjectId(receta_id)})
        if data:
            data["id"] = str(data.pop("_id"))
            # Convertir los dicts de medicamentos a objetos Medicamento
            data["medicamentos"] = [Medicamento(**m) for m in data.get("medicamentos", [])]
            return Receta(**data)
        return None

    def actualizar(self, receta_id: str, receta: Receta):
        data = asdict(receta)
        if 'id' in data: del data['id']
        self.collection.update_one({"_id": ObjectId(receta_id)}, {"": data})

    def eliminar(self, receta_id: str):
        self.collection.delete_one({"_id": ObjectId(receta_id)})
