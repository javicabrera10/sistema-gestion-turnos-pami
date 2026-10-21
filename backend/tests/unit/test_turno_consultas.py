from datetime import datetime

import mongomock
import pytest

from app.models.turno import EstadoTurno
from app.repositories.turno_repository import TurnoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.utils.database import crear_indices, seed_usuarios
from app.utils.serializers import serializar_turno_con_paciente


@pytest.fixture
def db():
    db = mongomock.MongoClient()["pami_test_consultas_turnos"]
    crear_indices(db)
    seed_usuarios(db)
    return db


@pytest.fixture
def turnos(db):
    return TurnoRepository(db)


@pytest.fixture
def usuarios(db):
    return UsuarioRepository(db)


def _doc(paciente_id="p1", fecha=datetime(2099, 1, 1, 10, 0), estado="solicitado"):
    return {
        "paciente_id": paciente_id,
        "especialidad": "Cardiología",
        "fecha_hora": fecha,
        "motivo": "Control",
        "estado": estado,
        "medico_id": None,
        "administrativo_id": None,
    }


def test_listar_sin_filtro_devuelve_todos_ordenados_por_fecha(turnos):
    turnos.crear(_doc("p1", datetime(2099, 3, 1, 10, 0)))
    turnos.crear(_doc("p2", datetime(2099, 2, 1, 10, 0)))

    lista = turnos.listar()

    assert [t["fecha_hora"].month for t in lista] == [2, 3]


def test_listar_filtra_por_estado(turnos):
    turnos.crear(_doc(estado="solicitado"))
    turnos.crear(_doc(estado="otorgado"))

    lista = turnos.listar(EstadoTurno.SOLICITADO)

    assert len(lista) == 1
    assert lista[0]["estado"] == "solicitado"


def test_registrar_otorgamiento_guarda_todos_los_campos(turnos):
    id_ = turnos.crear(_doc())
    nueva_fecha = datetime(2099, 5, 5, 9, 30)

    turnos.registrar_otorgamiento(id_, "medico-1", nueva_fecha, "admin-1", EstadoTurno.OTORGADO)

    turno = turnos.get_by_id(id_)
    assert turno["estado"] == "otorgado"
    assert turno["medico_id"] == "medico-1"
    assert turno["administrativo_id"] == "admin-1"
    assert turno["fecha_hora"] == nueva_fecha


def test_buscar_por_ids_devuelve_solo_los_pedidos_sin_password(usuarios):
    paciente = usuarios.buscar_por_email("paciente@pamiapp.com")
    medico = usuarios.buscar_por_email("medico@pamiapp.com")

    encontrados = usuarios.buscar_por_ids([str(paciente["_id"]), str(medico["_id"])])

    assert {u["email"] for u in encontrados} == {"paciente@pamiapp.com", "medico@pamiapp.com"}
    assert all("password_hash" not in u for u in encontrados)


def test_serializar_con_paciente_solo_expone_datos_de_contacto(turnos, usuarios):
    paciente = usuarios.buscar_por_email("paciente@pamiapp.com")
    id_ = turnos.crear(_doc(str(paciente["_id"])))
    doc = {**turnos.get_by_id(id_), "paciente": paciente}

    salida = serializar_turno_con_paciente(doc)

    assert set(salida["paciente"]) == {"id", "nombre", "dni", "telefono"}
    assert salida["paciente"]["nombre"] == "Paula Paciente"
    assert salida["id"] == id_
    assert salida["fecha_hora"] == "2099-01-01T10:00:00"


def test_serializar_con_paciente_inexistente(turnos):
    id_ = turnos.crear(_doc())
    salida = serializar_turno_con_paciente({**turnos.get_by_id(id_), "paciente": None})
    assert salida["paciente"] is None
