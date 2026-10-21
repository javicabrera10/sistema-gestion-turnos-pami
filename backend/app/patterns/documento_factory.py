from app.models.receta import Receta

class DocumentoFactory:
    @staticmethod
    def crear_receta(paciente_id: str, medico_id: str) -> Receta:
        return Receta(paciente_id=paciente_id, medico_id=medico_id)

    @staticmethod
    def crear_orden(paciente_id: str, medico_id: str) -> dict:
        # Placeholder para futuras órdenes médicas
        return {"tipo": "orden", "paciente_id": paciente_id, "medico_id": medico_id}
