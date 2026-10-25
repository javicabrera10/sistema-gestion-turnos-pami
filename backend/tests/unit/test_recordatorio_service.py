from datetime import datetime, timedelta, timezone

import mongomock
import pytest

from app.models.turno import EstadoTurno
from app.patterns.recordatorio_strategy import Recordar2Horas, ReglaRecordatorio
from app.repositories.notificacion_repository import NotificacionRepository
from app.repositories.turno_repository import TurnoRepository
from app.services.notificacion_service import NotificacionService
from app.services.recordatorio_service import RecordatorioService, ahora_local

AHORA = datetime(2099, 5, 10, 8, 0)


@pytest.fixture
def entorno():
    db = mongomock.MongoClient()["pami_test_recordatorios"]
    turnos = TurnoRepository(db)
    notificaciones = NotificacionService(NotificacionRepository(db))
    return turnos, notificaciones


@pytest.fixture
def servicio(entorno):
    return RecordatorioService(*entorno)


def _turno(turnos, faltan: timedelta, estado=EstadoTurno.CONFIRMADO, paciente="p1") -> str:
    return turnos.crear(
        {
            "paciente_id": paciente,
            "especialidad": "Cardiología",
            "fecha_hora": AHORA + faltan,
            "motivo": "Control",
            "estado": estado.value,
            "medico_id": "m1",
            "administrativo_id": "a1",
        }
    )


def test_crea_un_recordatorio_para_un_turno_confirmado_de_manana(servicio, entorno):
    turnos, notificaciones = entorno
    id_ = _turno(turnos, timedelta(hours=20))

    assert servicio.procesar(AHORA) == 1

    notif = notificaciones.listar_mias("p1")[0]
    assert notif["tipo"] == "recordatorio"
    assert notif["turno_id"] == id_
    assert "Cardiología" in notif["mensaje"] and "04:00 hs" in notif["mensaje"]
    assert turnos.get_by_id(id_)["recordatorios_enviados"] == ["24h"]


def test_ejecutarlo_dos_veces_no_duplica_los_avisos(servicio, entorno):
    turnos, notificaciones = entorno
    _turno(turnos, timedelta(hours=20))

    assert servicio.procesar(AHORA) == 1
    assert servicio.procesar(AHORA) == 0
    assert servicio.procesar(AHORA + timedelta(hours=1)) == 0
    assert len(notificaciones.listar_mias("p1")) == 1


def test_a_las_2_horas_llega_un_segundo_recordatorio(servicio, entorno):
    turnos, notificaciones = entorno
    id_ = _turno(turnos, timedelta(hours=20))
    servicio.procesar(AHORA)

    assert servicio.procesar(AHORA + timedelta(hours=18, minutes=30)) == 1

    assert len(notificaciones.listar_mias("p1")) == 2
    assert sorted(turnos.get_by_id(id_)["recordatorios_enviados"]) == ["24h", "2h"]


def test_un_turno_cercano_recibe_un_solo_aviso_aunque_apliquen_las_dos_reglas(servicio, entorno):
    turnos, notificaciones = entorno
    id_ = _turno(turnos, timedelta(hours=1))

    assert servicio.procesar(AHORA) == 1
    assert servicio.procesar(AHORA + timedelta(minutes=10)) == 0

    assert len(notificaciones.listar_mias("p1")) == 1
    assert sorted(turnos.get_by_id(id_)["recordatorios_enviados"]) == ["24h", "2h"]


@pytest.mark.parametrize("estado", [EstadoTurno.SOLICITADO, EstadoTurno.OTORGADO, EstadoTurno.REPROGRAMADO, EstadoTurno.RECHAZADO, EstadoTurno.CANCELADO])
def test_solo_se_recuerdan_los_turnos_confirmados(servicio, entorno, estado):
    turnos, notificaciones = entorno
    _turno(turnos, timedelta(hours=5), estado=estado)

    assert servicio.procesar(AHORA) == 0
    assert notificaciones.listar_mias("p1") == []


@pytest.mark.parametrize("faltan", [timedelta(hours=-3), timedelta(0), timedelta(hours=25), timedelta(days=7)])
def test_no_recuerda_turnos_pasados_ni_lejanos(servicio, entorno, faltan):
    turnos, _ = entorno
    _turno(turnos, faltan)

    assert servicio.procesar(AHORA) == 0


def test_cada_paciente_recibe_el_aviso_de_su_turno(servicio, entorno):
    turnos, notificaciones = entorno
    _turno(turnos, timedelta(hours=5), paciente="p1")
    _turno(turnos, timedelta(hours=6), paciente="p2")

    assert servicio.procesar(AHORA) == 2
    assert len(notificaciones.listar_mias("p1")) == 1
    assert len(notificaciones.listar_mias("p2")) == 1


def test_si_se_reprograma_el_turno_los_recordatorios_empiezan_de_nuevo(servicio, entorno):
    turnos, notificaciones = entorno
    id_ = _turno(turnos, timedelta(hours=5))
    servicio.procesar(AHORA)

    nueva = AHORA + timedelta(days=3)
    turnos.registrar_reprogramacion(id_, nueva, "a1", EstadoTurno.REPROGRAMADO)
    turnos.actualizar_estado(id_, EstadoTurno.CONFIRMADO)

    assert servicio.procesar(nueva - timedelta(hours=10)) == 1
    assert len(notificaciones.listar_mias("p1")) == 2


def test_se_puede_cambiar_la_regla_sin_tocar_el_servicio(entorno):
    turnos, notificaciones = entorno
    _turno(turnos, timedelta(hours=20))

    solo_2_horas = RecordatorioService(turnos, notificaciones, reglas=(Recordar2Horas(),))

    assert solo_2_horas.procesar(AHORA) == 0  # faltan 20 h y esta regla solo avisa a las 2 h
    assert solo_2_horas.procesar(AHORA + timedelta(hours=18, minutes=30)) == 1


def test_funciona_con_una_regla_propia(entorno):
    turnos, notificaciones = entorno
    _turno(turnos, timedelta(days=2))

    class RecordarConDosDias(ReglaRecordatorio):
        nombre = "2d"
        horas_antes = 48

        def debe_recordar(self, fecha_turno, ahora):
            return ahora < fecha_turno <= ahora + timedelta(days=2)

    servicio = RecordatorioService(turnos, notificaciones, reglas=(RecordarConDosDias(),))

    assert servicio.procesar(AHORA) == 1


def test_sin_reglas_no_hace_nada(entorno):
    turnos, _ = entorno
    _turno(turnos, timedelta(hours=1))

    assert RecordatorioService(*entorno, reglas=()).procesar(AHORA) == 0


def test_la_hora_local_es_utc_menos_3_y_se_puede_cambiar(monkeypatch):
    ahora_utc = datetime.now(timezone.utc).replace(tzinfo=None)

    monkeypatch.delenv("RECORDATORIOS_UTC_OFFSET", raising=False)
    assert abs((ahora_utc - ahora_local()) - timedelta(hours=3)) < timedelta(seconds=5)
    assert ahora_local().tzinfo is None

    monkeypatch.setenv("RECORDATORIOS_UTC_OFFSET", "0")
    assert abs(ahora_utc - ahora_local()) < timedelta(seconds=5)
