from datetime import datetime
from types import SimpleNamespace

import mongomock
import pytest

from app.models.turno import EstadoTurno
from app.patterns.turno_state import TransicionInvalida
from app.repositories.turno_repository import TurnoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.turno_admin_service import MedicoInvalido, TurnoAdminService
from app.services.turno_service import TurnoNoEncontrado, TurnoService
from app.utils.database import crear_indices, seed_usuarios

FECHA_PEDIDA = datetime(2099, 1, 1, 10, 0)
FECHA_OTORGADA = datetime(2099, 1, 3, 11, 30)


@pytest.fixture
def usuarios():
    db = mongomock.MongoClient()["pami_test_admin_service"]
    crear_indices(db)
    seed_usuarios(db)
    return UsuarioRepository(db), TurnoRepository(db)


@pytest.fixture
def ids(usuarios):
    repo_usuarios, _ = usuarios
    return SimpleNamespace(
        paciente=str(repo_usuarios.buscar_por_email("paciente@pamiapp.com")["_id"]),
        medico=str(repo_usuarios.buscar_por_email("medico@pamiapp.com")["_id"]),
        admin=str(repo_usuarios.buscar_por_email("admin@pamiapp.com")["_id"]),
    )


@pytest.fixture
def paciente_service(usuarios):
    return TurnoService(usuarios[1])


@pytest.fixture
def admin_service(usuarios):
    return TurnoAdminService(usuarios[1], usuarios[0])


def _solicitar(paciente_service, paciente_id):
    datos = SimpleNamespace(especialidad="Cardiología", fecha_hora=FECHA_PEDIDA, motivo="Control")
    return paciente_service.solicitar(paciente_id, datos)


def _datos_otorgar(medico_id):
    return SimpleNamespace(medico_id=medico_id, fecha_hora=FECHA_OTORGADA)


def test_listar_incluye_los_datos_del_paciente(admin_service, paciente_service, ids):
    _solicitar(paciente_service, ids.paciente)
    lista = admin_service.listar()
    assert len(lista) == 1
    assert lista[0]["paciente"]["nombre"] == "Paula Paciente"


def test_listar_filtra_por_estado(admin_service, paciente_service, ids):
    turno = _solicitar(paciente_service, ids.paciente)
    _solicitar(paciente_service, ids.paciente)
    admin_service.otorgar(str(turno["_id"]), ids.admin, _datos_otorgar(ids.medico))

    assert len(admin_service.listar(EstadoTurno.SOLICITADO)) == 1
    assert len(admin_service.listar(EstadoTurno.OTORGADO)) == 1


def test_obtener_un_turno(admin_service, paciente_service, ids):
    turno = _solicitar(paciente_service, ids.paciente)
    assert admin_service.obtener(str(turno["_id"]))["paciente"]["dni"] == "30111222"


@pytest.mark.parametrize("turno_id", ["no-es-un-id", "0" * 24])
def test_obtener_turno_inexistente(admin_service, turno_id):
    with pytest.raises(TurnoNoEncontrado):
        admin_service.obtener(turno_id)


def test_otorgar_asigna_medico_fecha_y_administrativo(admin_service, paciente_service, ids):
    turno = _solicitar(paciente_service, ids.paciente)

    otorgado = admin_service.otorgar(str(turno["_id"]), ids.admin, _datos_otorgar(ids.medico))

    assert otorgado["estado"] == "otorgado"
    assert otorgado["medico_id"] == ids.medico
    assert otorgado["administrativo_id"] == ids.admin
    assert otorgado["fecha_hora"] == FECHA_OTORGADA
    assert otorgado["paciente"]["nombre"] == "Paula Paciente"


def test_despues_de_otorgar_el_paciente_puede_confirmar(admin_service, paciente_service, ids):
    turno = _solicitar(paciente_service, ids.paciente)
    admin_service.otorgar(str(turno["_id"]), ids.admin, _datos_otorgar(ids.medico))

    confirmado = paciente_service.confirmar(str(turno["_id"]), ids.paciente)

    assert confirmado["estado"] == "confirmado"


def test_no_se_puede_otorgar_dos_veces(admin_service, paciente_service, ids):
    turno = _solicitar(paciente_service, ids.paciente)
    admin_service.otorgar(str(turno["_id"]), ids.admin, _datos_otorgar(ids.medico))
    with pytest.raises(TransicionInvalida):
        admin_service.otorgar(str(turno["_id"]), ids.admin, _datos_otorgar(ids.medico))


def test_medico_inexistente(admin_service, paciente_service, ids):
    turno = _solicitar(paciente_service, ids.paciente)
    with pytest.raises(MedicoInvalido):
        admin_service.otorgar(str(turno["_id"]), ids.admin, _datos_otorgar("0" * 24))


def test_el_usuario_elegido_tiene_que_ser_medico(admin_service, paciente_service, ids):
    turno = _solicitar(paciente_service, ids.paciente)
    with pytest.raises(MedicoInvalido):
        admin_service.otorgar(str(turno["_id"]), ids.admin, _datos_otorgar(ids.paciente))


@pytest.mark.parametrize("turno_id", ["no-es-un-id", "0" * 24])
def test_otorgar_turno_inexistente(admin_service, ids, turno_id):
    with pytest.raises(TurnoNoEncontrado):
        admin_service.otorgar(turno_id, ids.admin, _datos_otorgar(ids.medico))
