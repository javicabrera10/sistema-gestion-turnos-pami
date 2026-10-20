from datetime import datetime

import mongomock
import pytest

from app.models.turno import EstadoTurno
from app.repositories.turno_repository import TurnoRepository
from app.utils.database import crear_indices


@pytest.fixture
def repo():
    db = mongomock.MongoClient()["pami_test_repo_turnos"]
    crear_indices(db)
    return TurnoRepository(db)


def _doc(paciente_id="p1", fecha=datetime(2099, 1, 1, 10, 0)):
    return {
        "paciente_id": paciente_id,
        "especialidad": "Cardiología",
        "fecha_hora": fecha,
        "motivo": "Control",
        "estado": "solicitado",
        "medico_id": None,
        "administrativo_id": None,
    }


def test_crear_y_buscar_por_id(repo):
    id_ = repo.crear(_doc())
    assert repo.get_by_id(id_)["motivo"] == "Control"


def test_id_mal_formado_devuelve_none(repo):
    assert repo.get_by_id("no-es-un-id") is None


def test_id_inexistente_devuelve_none(repo):
    assert repo.get_by_id("0" * 24) is None


def test_listar_solo_los_del_paciente_ordenados_por_fecha(repo):
    repo.crear(_doc("p1", datetime(2099, 3, 1, 10, 0)))
    repo.crear(_doc("p1", datetime(2099, 2, 1, 10, 0)))
    repo.crear(_doc("p2", datetime(2099, 1, 1, 10, 0)))

    turnos = repo.listar_por_paciente("p1")

    assert [t["fecha_hora"].month for t in turnos] == [2, 3]
    assert all(t["paciente_id"] == "p1" for t in turnos)


def test_actualizar_estado_guarda_el_texto(repo):
    id_ = repo.crear(_doc())
    repo.actualizar_estado(id_, EstadoTurno.OTORGADO)
    assert repo.get_by_id(id_)["estado"] == "otorgado"
