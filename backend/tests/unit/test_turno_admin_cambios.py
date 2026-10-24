from datetime import datetime
from types import SimpleNamespace

import mongomock
import pytest

from app.models.turno import EstadoTurno
from app.patterns.observer import EventBus, TURNO_CANCELADO, TURNO_REPROGRAMADO
from app.patterns.turno_state import TransicionInvalida
from app.repositories.turno_repository import TurnoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.turno_admin_service import HorarioOcupado, TurnoAdminService
from app.services.turno_service import TurnoNoEncontrado, TurnoService
from app.utils.database import crear_indices, seed_usuarios

FECHA_PEDIDA = datetime(2099, 1, 1, 10, 0)
FECHA_OTORGADA = datetime(2099, 1, 3, 11, 30)
FECHA_NUEVA = datetime(2099, 1, 10, 9, 0)


@pytest.fixture
def entorno():
    db = mongomock.MongoClient()["pami_test_admin_cambios"]
    crear_indices(db)
    seed_usuarios(db)
    usuarios, turnos = UsuarioRepository(db), TurnoRepository(db)
    bus = EventBus()
    eventos = []
    bus.suscribir(TURNO_REPROGRAMADO, lambda d: eventos.append((TURNO_REPROGRAMADO, d)))
    bus.suscribir(TURNO_CANCELADO, lambda d: eventos.append((TURNO_CANCELADO, d)))
    return SimpleNamespace(
        admin=TurnoAdminService(turnos, usuarios, bus),
        paciente=TurnoService(turnos),
        turnos=turnos,
        eventos=eventos,
        paciente_id=str(usuarios.buscar_por_email("paciente@pamiapp.com")["_id"]),
        medico_id=str(usuarios.buscar_por_email("medico@pamiapp.com")["_id"]),
        admin_id=str(usuarios.buscar_por_email("admin@pamiapp.com")["_id"]),
    )


def _turno_otorgado(e):
    datos = SimpleNamespace(especialidad="Cardiología", fecha_hora=FECHA_PEDIDA, motivo="Control")
    turno = e.paciente.solicitar(e.paciente_id, datos)
    e.admin.otorgar(str(turno["_id"]), e.admin_id, SimpleNamespace(medico_id=e.medico_id, fecha_hora=FECHA_OTORGADA))
    return str(turno["_id"])


def test_reprogramar_cambia_fecha_y_estado_y_publica_el_evento(entorno):
    turno_id = _turno_otorgado(entorno)

    turno = entorno.admin.reprogramar(turno_id, entorno.admin_id, SimpleNamespace(fecha_hora=FECHA_NUEVA))

    assert turno["estado"] == "reprogramado"
    assert turno["fecha_hora"] == FECHA_NUEVA
    evento, datos = entorno.eventos[-1]
    assert evento == TURNO_REPROGRAMADO
    assert datos["paciente_id"] == entorno.paciente_id
    assert datos["fecha_hora"] == FECHA_NUEVA
    assert datos["administrativo_id"] == entorno.admin_id


def test_cancelar_cambia_el_estado_y_publica_el_evento(entorno):
    turno_id = _turno_otorgado(entorno)

    turno = entorno.admin.cancelar(turno_id, entorno.admin_id)

    assert turno["estado"] == "cancelado"
    assert entorno.eventos[-1][0] == TURNO_CANCELADO


def test_no_se_reprograma_ni_cancela_un_turno_solicitado(entorno):
    datos = SimpleNamespace(especialidad="Cardiología", fecha_hora=FECHA_PEDIDA, motivo="Control")
    turno_id = str(entorno.paciente.solicitar(entorno.paciente_id, datos)["_id"])

    with pytest.raises(TransicionInvalida):
        entorno.admin.reprogramar(turno_id, entorno.admin_id, SimpleNamespace(fecha_hora=FECHA_NUEVA))
    with pytest.raises(TransicionInvalida):
        entorno.admin.cancelar(turno_id, entorno.admin_id)
    assert entorno.eventos == []  # si la transición falla no se avisa a nadie


def test_un_turno_cancelado_no_se_puede_cancelar_de_nuevo(entorno):
    turno_id = _turno_otorgado(entorno)
    entorno.admin.cancelar(turno_id, entorno.admin_id)

    with pytest.raises(TransicionInvalida):
        entorno.admin.cancelar(turno_id, entorno.admin_id)


def test_no_se_reprograma_a_un_horario_ocupado_del_medico(entorno):
    primero = _turno_otorgado(entorno)  # ocupa FECHA_OTORGADA con el médico
    datos = SimpleNamespace(especialidad="Pediatría", fecha_hora=FECHA_PEDIDA, motivo="Control")
    segundo = str(entorno.paciente.solicitar(entorno.paciente_id, datos)["_id"])
    entorno.admin.otorgar(segundo, entorno.admin_id, SimpleNamespace(medico_id=entorno.medico_id, fecha_hora=FECHA_NUEVA))

    with pytest.raises(HorarioOcupado):
        entorno.admin.reprogramar(primero, entorno.admin_id, SimpleNamespace(fecha_hora=FECHA_NUEVA))
    assert entorno.turnos.get_by_id(primero)["estado"] == EstadoTurno.OTORGADO.value


def test_un_turno_reprogramado_sigue_ocupando_el_horario(entorno):
    turno_id = _turno_otorgado(entorno)
    entorno.admin.reprogramar(turno_id, entorno.admin_id, SimpleNamespace(fecha_hora=FECHA_NUEVA))

    assert entorno.turnos.horario_ocupado(entorno.medico_id, FECHA_NUEVA) is True


def test_turno_inexistente(entorno):
    with pytest.raises(TurnoNoEncontrado):
        entorno.admin.cancelar("0" * 24, entorno.admin_id)
    with pytest.raises(TurnoNoEncontrado):
        entorno.admin.reprogramar("no-es-un-id", entorno.admin_id, SimpleNamespace(fecha_hora=FECHA_NUEVA))
