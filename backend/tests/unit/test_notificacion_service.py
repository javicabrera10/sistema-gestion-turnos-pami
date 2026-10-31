from datetime import datetime

import mongomock
import pytest

from app.repositories.notificacion_repository import NotificacionRepository
from app.services.notificacion_service import NotificacionNoEncontrada, NotificacionService

FECHA = datetime(2099, 11, 5, 10, 30)


def _datos(**extra):
    return {
        "turno_id": "t1",
        "paciente_id": "p1",
        "medico_id": "m1",
        "administrativo_id": "a1",
        "especialidad": "Cardiología",
        "fecha_hora": FECHA,
        **extra,
    }


@pytest.fixture
def service():
    db = mongomock.MongoClient()["pami_test_service_notificaciones"]
    return NotificacionService(NotificacionRepository(db))


def test_turno_reprogramado_avisa_al_paciente_la_nueva_fecha(service):
    service.crear_turno_reprogramado(_datos())

    notif = service.listar_mias("p1")[0]
    assert notif["tipo"] == "turno_reprogramado"
    assert notif["leida"] is False
    assert "05/11/2099 a las 10:30 hs" in notif["mensaje"]
    assert "Cardiología" in notif["mensaje"]


def test_turno_cancelado_avisa_al_paciente(service):
    service.crear_turno_cancelado(_datos())

    notif = service.listar_mias("p1")[0]
    assert notif["tipo"] == "turno_cancelado"
    assert "05/11/2099" in notif["mensaje"]


def test_el_mensaje_funciona_sin_especialidad(service):
    service.crear_turno_cancelado(_datos(especialidad=None))
    assert service.listar_mias("p1")[0]["mensaje"].startswith("Cancelaron tu turno del")


@pytest.mark.parametrize("aceptado, tipo, verbo", [(True, "turno_confirmado", "confirmó"), (False, "turno_rechazado", "rechazó")])
def test_la_respuesta_del_paciente_le_llega_al_administrativo(service, aceptado, tipo, verbo):
    service.crear_respuesta_paciente(_datos(), aceptado, paciente_nombre="Paula Paciente")

    assert service.listar_mias("p1") == []  # no se la manda al paciente
    notif = service.listar_mias("a1")[0]
    assert notif["tipo"] == tipo
    assert notif["mensaje"].startswith(f"Paula Paciente {verbo}")


def test_la_respuesta_sin_nombre_usa_un_texto_generico(service):
    service.crear_respuesta_paciente(_datos(), True)
    assert service.listar_mias("a1")[0]["mensaje"].startswith("El paciente confirmó")


def test_la_respuesta_sin_administrativo_no_crea_nada(service):
    assert service.crear_respuesta_paciente(_datos(administrativo_id=None), True) is None
    assert service.listar_mias("a1") == []


def test_no_se_marca_como_leida_la_notificacion_de_otro(service):
    id_ = service.crear_turno_cancelado(_datos())
    with pytest.raises(NotificacionNoEncontrada):
        service.marcar_leida(id_, "otra-persona")
    assert service.marcar_leida(id_, "p1")["leida"] is True


def test_recordatorio_avisa_al_paciente_el_dia_y_la_hora(service):
    service.crear_recordatorio(_datos())

    notif = service.listar_mias("p1")[0]
    assert notif["tipo"] == "recordatorio"
    assert notif["mensaje"] == "Recordatorio: tenés un turno de Cardiología el 05/11/2099 a las 10:30 hs."


def test_receta_emitida_le_avisa_al_administrativo_sin_datos_de_salud(service):
    service.crear_receta_emitida("a1", {"receta_id": "r1"}, medico_nombre="Martín Médico", paciente_nombre="Paula Paciente")

    notif = service.listar_mias("a1")[0]
    assert notif["tipo"] == "receta_emitida"
    assert notif["receta_id"] == "r1"
    assert notif["leida"] is False
    assert notif["mensaje"].startswith("Martín Médico emitió una receta con plan de medicación para Paula Paciente.")
    assert "Generar recordatorios" in notif["mensaje"]
    assert "turno_id" not in notif  # no es un aviso de turno


def test_receta_emitida_funciona_sin_nombres(service):
    service.crear_receta_emitida("a1", {"receta_id": "r1"})
    assert service.listar_mias("a1")[0]["mensaje"].startswith("Un médico emitió una receta con plan de medicación para un paciente.")


def test_resolver_receta_emitida_solo_marca_los_avisos_de_esa_receta(service):
    service.crear_receta_emitida("a1", {"receta_id": "r1"})
    service.crear_receta_emitida("a2", {"receta_id": "r1"})
    service.crear_receta_emitida("a1", {"receta_id": "r2"})

    service.resolver_receta_emitida("r1")

    assert [n["leida"] for n in service.listar_mias("a1")] == [False, True]  # la más nueva (r2) primero
    assert service.listar_mias("a2")[0]["leida"] is True
