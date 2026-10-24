"""Patrón Factory: un solo lugar que sabe cómo armar cada tipo de documento médico."""

from app.models.receta import Medicamento, Receta, TipoReceta


class DocumentoFactory:
    @staticmethod
    def crear_receta(paciente_id: str, medico_id: str, medicamentos=None, indicaciones: str = "") -> Receta:
        return Receta(
            tipo=TipoReceta.RECETA.value,
            paciente_id=paciente_id,
            medico_id=medico_id,
            indicaciones=indicaciones,
            medicamentos=[Medicamento(**m) for m in (medicamentos or [])],
        )

    @staticmethod
    def crear_orden(paciente_id: str, medico_id: str, indicaciones: str = "") -> Receta:
        # La orden (estudio o práctica) no lleva medicamentos: todo va en las indicaciones
        return Receta(
            tipo=TipoReceta.ORDEN.value,
            paciente_id=paciente_id,
            medico_id=medico_id,
            indicaciones=indicaciones,
        )

    @classmethod
    def crear(cls, tipo: str, paciente_id: str, medico_id: str, medicamentos=None, indicaciones: str = "") -> Receta:
        if tipo == TipoReceta.ORDEN.value:
            return cls.crear_orden(paciente_id, medico_id, indicaciones)
        return cls.crear_receta(paciente_id, medico_id, medicamentos, indicaciones)
