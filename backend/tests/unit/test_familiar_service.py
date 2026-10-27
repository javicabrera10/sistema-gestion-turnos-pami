from datetime import datetime, timedelta
from types import SimpleNamespace

import mongomock
import pytest

from app.repositories.familiar_repository import FamiliarRepository, MensajeFamiliarRepository
from app.services.familiar_service import FamiliarService
from app.utils.database import crear_indices


@pytest.fixture
def entorno():
    db = mongomock.MongoClient()["pami_test_familiar"]
    crear_indices(db)
    mensajes = MensajeFamiliarRepository(db)
    return SimpleNamespace(service=FamiliarService(FamiliarRepository(db), mensajes), mensajes=mensajes, db=db)


def _datos(nombre="Marta Gómez", canal="sms", contacto="+5492615551234"):
    return SimpleNamespace(nombre=nombre, parentesco="Hija", canal=canal, contacto=contacto)


def test_sin_autorizacion_no_hay_familiar(entorno):
    assert entorno.service.obtener("p1") is None


def test_guardar_autoriza_al_familiar_y_registra_cuando(entorno):
    familiar = entorno.service.guardar("p1", _datos())

    assert familiar["nombre"] == "Marta Gómez"
    assert familiar["canal"] == "sms"
    assert familiar["paciente_id"] == "p1"
    assert isinstance(familiar["autorizado_en"], datetime)
    assert "consentimiento" not in familiar  # el consentimiento se valida en el schema, no se guarda como dato


def test_guardar_de_nuevo_reemplaza_al_familiar_anterior(entorno):
    entorno.service.guardar("p1", _datos(nombre="Marta Gómez"))
    entorno.service.guardar("p1", _datos(nombre="Luis Pérez", canal="email", contacto="luis@mail.com"))

    assert entorno.db.familiares_autorizados.count_documents({"paciente_id": "p1"}) == 1
    familiar = entorno.service.obtener("p1")
    assert (familiar["nombre"], familiar["canal"], familiar["contacto"]) == ("Luis Pérez", "email", "luis@mail.com")


def test_cada_paciente_tiene_su_propio_familiar(entorno):
    entorno.service.guardar("p1", _datos(nombre="Marta Gómez"))
    entorno.service.guardar("p2", _datos(nombre="Luis Pérez"))

    assert entorno.service.obtener("p1")["nombre"] == "Marta Gómez"
    assert entorno.service.obtener("p2")["nombre"] == "Luis Pérez"


def test_revocar_quita_la_autorizacion(entorno):
    entorno.service.guardar("p1", _datos())

    assert entorno.service.revocar("p1") is True
    assert entorno.service.obtener("p1") is None


def test_revocar_sin_familiar_no_falla(entorno):
    assert entorno.service.revocar("p1") is False


def test_revocar_no_toca_al_familiar_de_otro_paciente(entorno):
    entorno.service.guardar("p1", _datos())
    entorno.service.guardar("p2", _datos(nombre="Luis Pérez"))

    entorno.service.revocar("p1")

    assert entorno.service.obtener("p2")["nombre"] == "Luis Pérez"


def _aviso(entorno, paciente, texto, minutos):
    entorno.mensajes.crear(
        {
            "paciente_id": paciente,
            "canal": "sms",
            "destino": "+5492615551234",
            "texto": texto,
            "evento": "turno.otorgado",
            "estado": "enviado (simulado)",
            "creado_en": datetime(2099, 1, 1, 10, 0) + timedelta(minutes=minutos),
        }
    )


def test_los_avisos_se_listan_del_mas_nuevo_al_mas_viejo(entorno):
    _aviso(entorno, "p1", "primero", 0)
    _aviso(entorno, "p1", "segundo", 5)
    _aviso(entorno, "p1", "tercero", 10)

    assert [a["texto"] for a in entorno.service.listar_avisos("p1")] == ["tercero", "segundo", "primero"]


def test_los_avisos_son_solo_los_del_paciente(entorno):
    _aviso(entorno, "p1", "de p1", 0)
    _aviso(entorno, "p2", "de p2", 1)

    assert [a["texto"] for a in entorno.service.listar_avisos("p1")] == ["de p1"]


def test_la_lista_de_avisos_se_limita_a_los_ultimos_50(entorno):
    for i in range(60):
        _aviso(entorno, "p1", f"aviso {i}", i)

    avisos = entorno.service.listar_avisos("p1")

    assert len(avisos) == 50
    assert avisos[0]["texto"] == "aviso 59"
