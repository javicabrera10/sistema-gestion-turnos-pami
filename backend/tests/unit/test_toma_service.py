from datetime import datetime

import mongomock
import pytest

from app.models.receta import EstadoReceta
from app.repositories.notificacion_repository import NotificacionRepository
from app.repositories.receta_repository import RecetaRepository
from app.services.notificacion_service import NotificacionService
from app.services.toma_service import TomaMedicacionService
from app.utils.database import crear_indices

AHORA = datetime(2099, 1, 1, 12, 0)


@pytest.fixture
def entorno():
    db = mongomock.MongoClient()["pami_test_tomas"]
    crear_indices(db)
    notificaciones = NotificacionService(NotificacionRepository(db))
    return RecetaRepository(db), notificaciones


@pytest.fixture
def servicio(entorno):
    recetas, notificaciones = entorno
    return TomaMedicacionService(recetas, notificaciones)


def _item(medicamento="Ibuprofeno", dosis="400 mg", horarios=("08:00", "16:00"), dias=5):
    return {"medicamento": medicamento, "dosis": dosis, "horarios": list(horarios), "duracion_dias": dias}


def _receta(recetas, plan, paciente="p1", tipo="receta", estado=EstadoReceta.EMITIDA.value, indicaciones="", **extra) -> str:
    return recetas.crear(
        {
            "tipo": tipo,
            "paciente_id": paciente,
            "medico_id": "m1",
            "indicaciones": indicaciones,
            "medicamentos": [],
            "plan_medicacion": plan,
            "estado": estado,
            "fecha": AHORA,
            **extra,
        }
    )


def test_entrega_al_paciente_la_receta_con_el_plan_de_toma(servicio, entorno):
    recetas, notificaciones = entorno
    id_ = _receta(recetas, [_item()], indicaciones="Después de las comidas.")

    assert servicio.procesar(AHORA) == 1

    aviso = notificaciones.listar_mias("p1")[0]
    assert aviso["tipo"] == "toma_medicacion"
    assert aviso["receta_id"] == id_
    assert "turno_id" not in aviso
    assert aviso["leida"] is False
    assert aviso["mensaje"] == (
        "Tu médico te emitió una receta. Plan de toma: Ibuprofeno (400 mg) a las 08:00, 16:00 hs durante 5 días. "
        "Indicaciones: Después de las comidas."
    )


def test_es_un_solo_aviso_por_receta_aunque_haya_varios_horarios(servicio, entorno):
    recetas, notificaciones = entorno
    _receta(recetas, [_item(horarios=("08:00", "12:00", "16:00", "20:00"))])

    assert servicio.procesar(AHORA) == 1
    assert len(notificaciones.listar_mias("p1")) == 1


def test_varios_medicamentos_van_en_el_mismo_aviso(servicio, entorno):
    recetas, notificaciones = entorno
    _receta(recetas, [_item("Ibuprofeno", "400 mg", ("08:00",), 5), _item("Omeprazol", "20 mg", ("07:00",), 1)])

    assert servicio.procesar(AHORA) == 1
    mensaje = notificaciones.listar_mias("p1")[0]["mensaje"]
    assert "Ibuprofeno (400 mg) a las 08:00 hs durante 5 días" in mensaje
    assert "Omeprazol (20 mg) a las 07:00 hs durante 1 día" in mensaje


def test_sin_indicaciones_el_mensaje_no_las_menciona(servicio, entorno):
    recetas, notificaciones = entorno
    _receta(recetas, [_item()])

    servicio.procesar(AHORA)

    assert "Indicaciones" not in notificaciones.listar_mias("p1")[0]["mensaje"]


def test_ejecutarlo_dos_veces_no_duplica_el_aviso(servicio, entorno):
    recetas, notificaciones = entorno
    id_ = _receta(recetas, [_item()])

    assert servicio.procesar(AHORA) == 1
    assert servicio.procesar(AHORA) == 0
    assert len(notificaciones.listar_mias("p1")) == 1
    assert recetas.get_by_id(id_)["recordatorio_generado_en"] == AHORA


def test_si_otro_administrativo_ya_lo_genero_no_se_repite(servicio, entorno):
    recetas, notificaciones = entorno
    id_ = _receta(recetas, [_item()])
    assert recetas.reclamar_recordatorio(id_, AHORA) is True  # el otro administrativo llegó primero

    assert servicio.procesar(AHORA) == 0
    assert notificaciones.listar_mias("p1") == []
    assert recetas.reclamar_recordatorio(id_, AHORA) is False


@pytest.mark.parametrize(
    "extra",
    [
        {"estado": EstadoReceta.BORRADOR.value},  # el paciente todavía no la ve
        {"tipo": "orden"},  # una orden no tiene medicamentos
    ],
)
def test_ignora_recetas_que_no_corresponden(servicio, entorno, extra):
    recetas, notificaciones = entorno
    _receta(recetas, [_item()], **extra)

    assert servicio.procesar(AHORA) == 0
    assert notificaciones.listar_mias("p1") == []


def test_ignora_una_receta_sin_plan(servicio, entorno):
    recetas, _ = entorno
    _receta(recetas, [])

    assert servicio.procesar(AHORA) == 0


def test_cada_paciente_recibe_su_receta(servicio, entorno):
    recetas, notificaciones = entorno
    _receta(recetas, [_item()], paciente="p1")
    _receta(recetas, [_item("Amoxicilina", "500 mg", ("08:00",))], paciente="p2")

    assert servicio.procesar(AHORA) == 2
    assert "Ibuprofeno" in notificaciones.listar_mias("p1")[0]["mensaje"]
    assert "Amoxicilina" in notificaciones.listar_mias("p2")[0]["mensaje"]


def test_al_generar_el_aviso_se_marca_como_leido_el_pendiente_del_administrativo(servicio, entorno):
    recetas, notificaciones = entorno
    id_ = _receta(recetas, [_item()])
    notificaciones.crear_receta_emitida("a1", {"receta_id": id_}, "Martín Médico", "Paula Paciente")
    assert notificaciones.listar_mias("a1")[0]["leida"] is False

    servicio.procesar(AHORA)

    assert notificaciones.listar_mias("a1")[0]["leida"] is True


def test_sin_fecha_usa_la_hora_actual(servicio, entorno):
    recetas, _ = entorno
    id_ = _receta(recetas, [_item()])

    servicio.procesar()

    assert isinstance(recetas.get_by_id(id_)["recordatorio_generado_en"], datetime)
