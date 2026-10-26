from datetime import datetime, timedelta

import mongomock
import pytest

from app.models.receta import EstadoReceta
from app.repositories.aviso_toma_repository import AvisoTomaRepository
from app.repositories.notificacion_repository import NotificacionRepository
from app.repositories.receta_repository import RecetaRepository
from app.services.notificacion_service import NotificacionService
from app.services.recordatorio_service import a_hora_local
from app.services.toma_service import TomaMedicacionService
from app.utils.database import crear_indices

INICIO = datetime(2099, 1, 1, 7, 0)  # el plan empieza el 1/1 a las 07:00


@pytest.fixture(autouse=True)
def _sin_diferencia_horaria(monkeypatch):
    # con diferencia 0 la hora local es igual a la guardada: las fechas de las pruebas se leen directo
    monkeypatch.setenv("RECORDATORIOS_UTC_OFFSET", "0")


@pytest.fixture
def entorno():
    db = mongomock.MongoClient()["pami_test_tomas"]
    crear_indices(db)  # incluye el índice único de avisos_toma
    notificaciones = NotificacionService(NotificacionRepository(db))
    return db, RecetaRepository(db), notificaciones


@pytest.fixture
def servicio(entorno):
    db, recetas, notificaciones = entorno
    return TomaMedicacionService(recetas, AvisoTomaRepository(db), notificaciones)


def _item(medicamento="Ibuprofeno", dosis="400 mg", horarios=("08:00", "16:00"), dias=5):
    return {"medicamento": medicamento, "dosis": dosis, "horarios": list(horarios), "duracion_dias": dias}


def _receta(recetas, plan, paciente="p1", tipo="receta", estado=EstadoReceta.EMITIDA.value, inicio=INICIO) -> str:
    return recetas.crear(
        {
            "tipo": tipo,
            "paciente_id": paciente,
            "medico_id": "m1",
            "indicaciones": "",
            "medicamentos": [],
            "plan_medicacion": plan,
            "estado": estado,
            "fecha": INICIO,
            "inicio_plan": inicio,
        }
    )


def test_crea_el_aviso_a_la_hora_de_la_toma(servicio, entorno):
    _, recetas, notificaciones = entorno
    id_ = _receta(recetas, [_item()])

    assert servicio.procesar(datetime(2099, 1, 1, 8, 10)) == 1

    aviso = notificaciones.listar_mias("p1")[0]
    assert aviso["tipo"] == "toma_medicacion"
    assert aviso["receta_id"] == id_
    assert "turno_id" not in aviso
    assert aviso["mensaje"] == "Es hora de tomar Ibuprofeno (400 mg) a las 08:00 hs."
    assert aviso["leida"] is False


@pytest.mark.parametrize("ahora, esperado", [
    (datetime(2099, 1, 1, 8, 0), 1),   # justo a la hora
    (datetime(2099, 1, 1, 8, 30), 1),  # justo al borde de la ventana
    (datetime(2099, 1, 1, 8, 31), 0),  # ya pasaron más de 30 minutos
    (datetime(2099, 1, 1, 7, 59), 0),  # todavía no es la hora
])
def test_solo_avisa_dentro_de_la_ventana(servicio, entorno, ahora, esperado):
    _, recetas, _ = entorno
    _receta(recetas, [_item(horarios=("08:00",))])

    assert servicio.procesar(ahora) == esperado


def test_no_avisa_tomas_anteriores_al_inicio_del_plan(servicio, entorno):
    _, recetas, notificaciones = entorno
    # el plan empezó a las 08:05: la toma de las 08:00 de ese día ya no corresponde
    _receta(recetas, [_item(horarios=("08:00",))], inicio=datetime(2099, 1, 1, 8, 5))

    assert servicio.procesar(datetime(2099, 1, 1, 8, 10)) == 0
    assert notificaciones.listar_mias("p1") == []


def test_avisa_mientras_dura_el_tratamiento_y_deja_de_avisar_despues(servicio, entorno):
    _, recetas, _ = entorno
    # 2 días desde el 1/1 a las 07:00: termina el 3/1 a las 07:00
    _receta(recetas, [_item(horarios=("08:00", "16:00"), dias=2)])

    assert servicio.procesar(datetime(2099, 1, 2, 16, 5)) == 1  # día 2, todavía dentro
    assert servicio.procesar(datetime(2099, 1, 3, 8, 5)) == 0   # 3/1 08:00 ya es después del fin
    assert servicio.procesar(datetime(2099, 1, 3, 16, 5)) == 0


def test_ejecutarlo_dos_veces_no_duplica_los_avisos(servicio, entorno):
    _, recetas, notificaciones = entorno
    _receta(recetas, [_item(horarios=("08:00",))])

    assert servicio.procesar(datetime(2099, 1, 1, 8, 5)) == 1
    assert servicio.procesar(datetime(2099, 1, 1, 8, 5)) == 0
    assert servicio.procesar(datetime(2099, 1, 1, 8, 20)) == 0
    assert len(notificaciones.listar_mias("p1")) == 1


def test_cada_dia_se_avisa_de_nuevo(servicio, entorno):
    _, recetas, notificaciones = entorno
    _receta(recetas, [_item(horarios=("08:00",))])

    assert servicio.procesar(datetime(2099, 1, 1, 8, 5)) == 1
    assert servicio.procesar(datetime(2099, 1, 2, 8, 5)) == 1
    assert len(notificaciones.listar_mias("p1")) == 2


def test_dos_medicamentos_a_la_misma_hora_son_dos_avisos(servicio, entorno):
    _, recetas, notificaciones = entorno
    _receta(recetas, [_item("Ibuprofeno", "400 mg", ("08:00",)), _item("Omeprazol", "20 mg", ("08:00",))])

    assert servicio.procesar(datetime(2099, 1, 1, 8, 5)) == 2
    mensajes = {n["mensaje"] for n in notificaciones.listar_mias("p1")}
    assert any("Ibuprofeno" in m for m in mensajes) and any("Omeprazol" in m for m in mensajes)


def test_la_toma_de_las_23_50_se_avisa_pasada_la_medianoche(servicio, entorno):
    _, recetas, _ = entorno
    _receta(recetas, [_item(horarios=("23:50",))])

    assert servicio.procesar(datetime(2099, 1, 2, 0, 10)) == 1


@pytest.mark.parametrize(
    "extra",
    [
        {"estado": EstadoReceta.BORRADOR.value},  # el paciente todavía no la ve
        {"tipo": "orden"},  # una orden no tiene medicamentos
        {"inicio": None},  # sin inicio no se sabe desde cuándo corre el plan
    ],
)
def test_ignora_recetas_que_no_corresponden(servicio, entorno, extra):
    _, recetas, notificaciones = entorno
    _receta(recetas, [_item(horarios=("08:00",))], **extra)

    assert servicio.procesar(datetime(2099, 1, 1, 8, 5)) == 0
    assert notificaciones.listar_mias("p1") == []


def test_ignora_una_receta_sin_plan(servicio, entorno):
    _, recetas, _ = entorno
    _receta(recetas, [])

    assert servicio.procesar(datetime(2099, 1, 1, 8, 5)) == 0


def test_cada_paciente_recibe_el_aviso_de_su_receta(servicio, entorno):
    _, recetas, notificaciones = entorno
    _receta(recetas, [_item(horarios=("08:00",))], paciente="p1")
    _receta(recetas, [_item("Amoxicilina", "500 mg", ("08:00",))], paciente="p2")

    assert servicio.procesar(datetime(2099, 1, 1, 8, 5)) == 2
    assert "Ibuprofeno" in notificaciones.listar_mias("p1")[0]["mensaje"]
    assert "Amoxicilina" in notificaciones.listar_mias("p2")[0]["mensaje"]


def test_la_ventana_se_puede_cambiar(entorno):
    db, recetas, notificaciones = entorno
    _receta(recetas, [_item(horarios=("08:00",))])
    corto = TomaMedicacionService(recetas, AvisoTomaRepository(db), notificaciones, ventana_minutos=5)

    assert corto.procesar(datetime(2099, 1, 1, 8, 10)) == 0  # pasaron más de 5 minutos
    assert corto.procesar(datetime(2099, 1, 1, 7, 59)) == 0  # todavía no era la hora
    assert corto.procesar(datetime(2099, 1, 1, 8, 5)) == 1


def test_el_inicio_del_plan_se_pasa_a_hora_local(servicio, entorno, monkeypatch):
    _, recetas, _ = entorno
    monkeypatch.setenv("RECORDATORIOS_UTC_OFFSET", "-3")
    # guardado en UTC a las 12:00 = 09:00 hora local: la toma de las 08:00 de ese día es anterior al inicio
    _receta(recetas, [_item(horarios=("08:00", "16:00"))], inicio=datetime(2099, 1, 1, 12, 0))

    assert servicio.procesar(datetime(2099, 1, 1, 8, 5)) == 0
    assert servicio.procesar(datetime(2099, 1, 1, 16, 5)) == 1
    assert a_hora_local(datetime(2099, 1, 1, 12, 0)) == datetime(2099, 1, 1, 9, 0)
