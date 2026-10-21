from app.models.receta import Receta, Medicamento
from app.patterns.documento_factory import DocumentoFactory
from app.repositories.receta_repository import RecetaRepository

class RecetaService:
    def __init__(self, repo: RecetaRepository):
        self.repo = repo

    def crear_receta(self, paciente_id: str, medico_id: str, medicamentos_data: list) -> str:
        # Usamos el patrón Factory
        receta = DocumentoFactory.crear_receta(paciente_id, medico_id)
        receta.medicamentos = [Medicamento(**m) for m in medicamentos_data]
        return self.repo.crear(receta)

    def emitir_receta(self, receta_id: str, medico_id: str):
        receta = self.repo.get_by_id(receta_id)
        if not receta or receta.medico_id != medico_id:
            raise ValueError("Receta no encontrada o no autorizada")
        receta.estado = "EMITIDA"
        self.repo.actualizar(receta_id, receta)
