from types import SimpleNamespace

import mongomock
import pytest

from app.patterns.observer import EventBus
from app.repositories.receta_repository import RecetaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.receta import PlanSchema, RecetaCrearSchema, RecetaEditarSchema
from app.services.receta_service import (
    PacienteInvalido,
    PlanNoPermitido,
    RecetaNoEncontrada,
    RecetaService,
    RecetaYaEmitida,
)
from app.utils.database import crear_indices, seed_usuarios

MEDICAMENTO = {"nombre": "Ibuprofeno", "dosis": "400 mg"}
PLAN = {"plan": [{"medicamento": "Ibuprofeno", "dosis": "400 mg", "horarios": ["08:00"], "duracion_dias": 5}]}


@pytest.fixture
def entorno():
    db = mongomock.MongoClient()["pami_test_receta_service"]
    crear_indices(db)
    seed_usuarios(db)
    usuarios = UsuarioRepository(db)
    eventos = []
    bus = EventBus()
    bus.suscribir("receta.emitida", eventos.append)
    return SimpleNamespace(
        service=RecetaService(RecetaRepository(db), usuarios, bus),
        eventos=eventos,
        paciente=str(usuarios.buscar_por_email("paciente@pamiapp.com")["_id"]),
        medico=str(usuarios.buscar_por_email("medico@pamiapp.com")["_id"]),
        admin=str(usuarios.buscar_por_email("admin@pamiapp.com")["_id"]),
    )


def _receta(paciente_id, **extra):
    return RecetaCrearSchema.model_validate({"paciente_id": paciente_id, "medicamentos": [MEDICAMENTO], **extra})


def _orden(paciente_id):
    return RecetaCrearSchema.model_validate(
        {"tipo": "orden", "paciente_id": paciente_id, "indicaciones": "Análisis de sangre completo"}
    )


def test_crear_receta_queda_en_borrador_a_nombre_del_medico(entorno):
    receta = entorno.service.crear(entorno.medico, _receta(entorno.paciente))

    assert receta["estado"] == "borrador"
    assert receta["tipo"] == "receta"
    assert receta["medico_id"] == entorno.medico
    assert receta["medicamentos"][0]["nombre"] == "Ibuprofeno"


def test_crear_orden_guarda_las_indicaciones(entorno):
    orden = entorno.service.crear(entorno.medico, _orden(entorno.paciente))

    assert orden["tipo"] == "orden"
    assert orden["indicaciones"] == "Análisis de sangre completo"
    assert orden["medicamentos"] == []


@pytest.mark.parametrize("quien", ["medico", "admin"])
def test_el_paciente_debe_existir_y_ser_paciente(entorno, quien):
    inexistente = "f" * 24
    otro_rol = getattr(entorno, quien)
    for paciente_id in (inexistente, otro_rol):
        with pytest.raises(PacienteInvalido):
            entorno.service.crear(entorno.medico, _receta(paciente_id))


def test_un_medico_no_edita_la_receta_de_otro(entorno):
    receta = entorno.service.crear(entorno.medico, _receta(entorno.paciente))
    cambios = RecetaEditarSchema.model_validate({"indicaciones": "Cambio ajeno"})

    with pytest.raises(RecetaNoEncontrada):
        entorno.service.editar(str(receta["_id"]), "otro-medico", cambios)


def test_un_medico_no_elimina_ni_emite_la_receta_de_otro(entorno):
    receta = entorno.service.crear(entorno.medico, _receta(entorno.paciente))
    id_ = str(receta["_id"])

    with pytest.raises(RecetaNoEncontrada):
        entorno.service.eliminar(id_, "otro-medico")
    with pytest.raises(RecetaNoEncontrada):
        entorno.service.emitir(id_, "otro-medico")
    assert entorno.service.listar_del_medico(entorno.medico)  # sigue existiendo


def test_emitir_cambia_el_estado_y_publica_el_evento(entorno):
    receta = entorno.service.crear(entorno.medico, _receta(entorno.paciente))

    emitida = entorno.service.emitir(str(receta["_id"]), entorno.medico)

    assert emitida["estado"] == "emitida"
    assert entorno.eventos == [
        {"receta_id": str(receta["_id"]), "paciente_id": entorno.paciente, "medico_id": entorno.medico, "tipo": "receta"}
    ]


def test_no_se_puede_emitir_dos_veces(entorno):
    receta = entorno.service.crear(entorno.medico, _receta(entorno.paciente))
    entorno.service.emitir(str(receta["_id"]), entorno.medico)

    with pytest.raises(RecetaYaEmitida):
        entorno.service.emitir(str(receta["_id"]), entorno.medico)
    assert len(entorno.eventos) == 1


def test_una_receta_emitida_tambien_se_puede_editar_y_eliminar(entorno):
    receta = entorno.service.crear(entorno.medico, _receta(entorno.paciente))
    id_ = str(receta["_id"])
    entorno.service.emitir(id_, entorno.medico)

    editada = entorno.service.editar(id_, entorno.medico, RecetaEditarSchema.model_validate({"indicaciones": "Nueva"}))
    assert editada["indicaciones"] == "Nueva"
    assert editada["estado"] == "emitida"

    entorno.service.eliminar(id_, entorno.medico)
    assert entorno.service.listar_del_medico(entorno.medico) == []


def test_el_paciente_solo_ve_lo_emitido(entorno):
    borrador = entorno.service.crear(entorno.medico, _receta(entorno.paciente))
    emitida = entorno.service.crear(entorno.medico, _orden(entorno.paciente))
    entorno.service.emitir(str(emitida["_id"]), entorno.medico)

    vistas = entorno.service.listar_del_paciente(entorno.paciente)

    assert [str(r["_id"]) for r in vistas] == [str(emitida["_id"])]
    assert str(borrador["_id"]) not in [str(r["_id"]) for r in vistas]


def test_registrar_plan_en_una_receta(entorno):
    receta = entorno.service.crear(entorno.medico, _receta(entorno.paciente))

    con_plan = entorno.service.registrar_plan(str(receta["_id"]), entorno.medico, PlanSchema.model_validate(PLAN))

    assert con_plan["plan_medicacion"][0]["horarios"] == ["08:00"]
    assert con_plan["plan_medicacion"][0]["duracion_dias"] == 5


def test_una_orden_no_lleva_plan_de_medicacion(entorno):
    orden = entorno.service.crear(entorno.medico, _orden(entorno.paciente))

    with pytest.raises(PlanNoPermitido):
        entorno.service.registrar_plan(str(orden["_id"]), entorno.medico, PlanSchema.model_validate(PLAN))


def test_un_id_malformado_no_existe(entorno):
    with pytest.raises(RecetaNoEncontrada):
        entorno.service.emitir("no-es-un-id", entorno.medico)
