import logging
from dataclasses import asdict
from datetime import datetime, timezone

from app.models.receta import EstadoReceta, TipoReceta
from app.patterns.documento_factory import DocumentoFactory
from app.patterns.observer import RECETA_EMITIDA

log = logging.getLogger("pami.recetas")


def _ahora() -> datetime:
    # Mongo guarda datetimes en UTC sin zona horaria (igual que en el resto de la app)
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RecetaNoEncontrada(Exception):
    pass


class PacienteInvalido(Exception):
    pass


class RecetaYaEmitida(Exception):
    pass


class PlanNoPermitido(Exception):
    """El plan de medicación solo se registra en recetas, no en órdenes."""


class RecetaService:
    def __init__(self, recetas_repo, usuarios_repo=None, event_bus=None):
        self.repo = recetas_repo
        self.usuarios = usuarios_repo
        self.bus = event_bus

    def crear(self, medico_id: str, datos) -> dict:
        self._validar_paciente(datos.paciente_id)
        receta = DocumentoFactory.crear(
            datos.tipo,
            datos.paciente_id,
            medico_id,
            medicamentos=[m.model_dump() for m in datos.medicamentos],
            indicaciones=datos.indicaciones,
        )
        doc = asdict(receta)
        doc.pop("id")
        id_ = self.repo.crear(doc)
        # no se loguea el contenido clínico, solo los ids
        log.info("%s creada id=%s medico=%s paciente=%s", receta.tipo, id_, medico_id, datos.paciente_id)
        return self.repo.get_by_id(id_)

    def listar_del_medico(self, medico_id: str) -> list[dict]:
        return self.repo.listar_por_medico(medico_id)

    def listar_del_paciente(self, paciente_id: str) -> list[dict]:
        """El paciente solo ve lo que el médico ya emitió, nunca los borradores."""
        return self.repo.listar_por_paciente(paciente_id, solo_emitidas=True)

    def editar(self, receta_id: str, medico_id: str, datos) -> dict:
        receta = self._receta_del_medico(receta_id, medico_id)
        cambios = {}
        if datos.indicaciones is not None:
            cambios["indicaciones"] = datos.indicaciones
        if datos.medicamentos is not None:
            if receta["tipo"] == TipoReceta.ORDEN.value:
                raise ValueError("Una orden no lleva medicamentos")
            if not datos.medicamentos:
                raise ValueError("Una receta necesita al menos un medicamento")
            cambios["medicamentos"] = [m.model_dump() for m in datos.medicamentos]
        self.repo.actualizar(receta["_id"], cambios)
        log.info("receta editada id=%s medico=%s", receta["_id"], medico_id)
        return self.repo.get_by_id(receta["_id"])

    def eliminar(self, receta_id: str, medico_id: str) -> None:
        receta = self._receta_del_medico(receta_id, medico_id)
        self.repo.eliminar(receta["_id"])
        log.info("receta eliminada id=%s medico=%s", receta["_id"], medico_id)

    def emitir(self, receta_id: str, medico_id: str) -> dict:
        receta = self._receta_del_medico(receta_id, medico_id)
        if receta["estado"] == EstadoReceta.EMITIDA.value:
            raise RecetaYaEmitida()
        self.repo.actualizar(receta["_id"], {"estado": EstadoReceta.EMITIDA.value, "inicio_plan": _ahora()})
        emitida = self.repo.get_by_id(receta["_id"])
        log.info("receta emitida id=%s medico=%s paciente=%s", receta["_id"], medico_id, receta["paciente_id"])
        if self.bus is not None:
            self.bus.publicar(
                RECETA_EMITIDA,
                {
                    "receta_id": str(receta["_id"]),
                    "paciente_id": receta["paciente_id"],
                    "medico_id": medico_id,
                    "tipo": receta["tipo"],
                },
            )
        return emitida

    def registrar_plan(self, receta_id: str, medico_id: str, datos) -> dict:
        receta = self._receta_del_medico(receta_id, medico_id)
        if receta["tipo"] != TipoReceta.RECETA.value:
            raise PlanNoPermitido()
        cambios = {"plan_medicacion": [i.model_dump() for i in datos.plan]}
        if receta["estado"] == EstadoReceta.EMITIDA.value:
            # el paciente ya puede ver la receta: el tratamiento empieza cuando se carga el plan
            cambios["inicio_plan"] = _ahora()
        self.repo.actualizar(receta["_id"], cambios)
        log.info("plan de medicación registrado receta=%s medico=%s", receta["_id"], medico_id)
        return self.repo.get_by_id(receta["_id"])

    def _receta_del_medico(self, receta_id: str, medico_id: str) -> dict:
        receta = self.repo.get_by_id(receta_id)
        # Si es de otro médico se responde igual que si no existiera
        if receta is None or receta["medico_id"] != medico_id:
            log.warning("receta inexistente o ajena id=%s medico=%s", receta_id, medico_id)
            raise RecetaNoEncontrada()
        return receta

    def _validar_paciente(self, paciente_id: str) -> None:
        if self.usuarios is None:
            return
        paciente = self.usuarios.get_by_id(paciente_id)
        if paciente is None or paciente.get("rol") != "paciente":
            raise PacienteInvalido()
