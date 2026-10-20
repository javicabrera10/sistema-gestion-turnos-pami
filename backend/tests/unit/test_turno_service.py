from datetime import datetime
from types import SimpleNamespace

import mongomock
import pytest

from app.models.turno import EstadoTurno
from app.patterns.turno_state import TransicionInvalida
from app.repositories.turno_repository import TurnoRepository
from app.services.turno_service import TurnoNoEncontrado, TurnoService
from app.utils.database import crear_indices
from app.utils.serializers import serializar_turno


@pytest.fixture
def repo():
    db = mongomock.MongoClient()["pami_test_service_turnos"]
    crear_indices(db)
    return TurnoRepository(db)


@pytest.fixture
def service(repo):
    return TurnoService(repo)


def _datos(fecha=datetime(2099, 1, 1, 10, 0)):
    return SimpleNamespace(especialidad="Cardiología", fecha_hora=fecha, motivo="Control anual")


def _otorgar(repo, turno):
    repo.actualizar_estado(turno["_id"], EstadoTurno.OTORGADO)


def test_solicitar_crea_turno_solicitado_del_paciente(service):
    turno = service.solicitar("p1", _datos())
    assert turno["paciente_id"] == "p1"
    assert turno["estado"] == "solicitado"
    assert turno["medico_id"] is None
    assert turno["administrativo_id"] is None


def test_listar_devuelve_solo_los_del_paciente(service):
    service.solicitar("p1", _datos())
    service.solicitar("p2", _datos())
    assert len(service.listar_del_paciente("p1")) == 1


def test_confirmar_turno_otorgado(service, repo):
    turno = service.solicitar("p1", _datos())
    _otorgar(repo, turno)
    assert service.confirmar(str(turno["_id"]), "p1")["estado"] == "confirmado"


def test_rechazar_turno_otorgado(service, repo):
    turno = service.solicitar("p1", _datos())
    _otorgar(repo, turno)
    assert service.rechazar(str(turno["_id"]), "p1")["estado"] == "rechazado"


def test_no_se_puede_confirmar_un_turno_solo_solicitado(service):
    turno = service.solicitar("p1", _datos())
    with pytest.raises(TransicionInvalida):
        service.confirmar(str(turno["_id"]), "p1")


def test_no_se_puede_responder_dos_veces(service, repo):
    turno = service.solicitar("p1", _datos())
    _otorgar(repo, turno)
    service.confirmar(str(turno["_id"]), "p1")
    with pytest.raises(TransicionInvalida):
        service.rechazar(str(turno["_id"]), "p1")


def test_turno_de_otro_paciente_no_se_encuentra(service, repo):
    turno = service.solicitar("p1", _datos())
    _otorgar(repo, turno)
    with pytest.raises(TurnoNoEncontrado):
        service.confirmar(str(turno["_id"]), "p2")


@pytest.mark.parametrize("turno_id", ["no-es-un-id", "0" * 24])
def test_turno_inexistente(service, turno_id):
    with pytest.raises(TurnoNoEncontrado):
        service.confirmar(turno_id, "p1")


def test_serializar_turno_devuelve_id_y_fecha_en_texto(service):
    turno = service.solicitar("p1", _datos())
    salida = serializar_turno(turno)
    assert salida["id"] == str(turno["_id"])
    assert "_id" not in salida
    assert salida["fecha_hora"] == "2099-01-01T10:00:00"
