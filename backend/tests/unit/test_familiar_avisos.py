import logging
from datetime import datetime
from types import SimpleNamespace

import mongomock
import pytest

from app.patterns.canal_strategy import CANALES, CanalEnvio
from app.patterns.observer import (
    TURNO_CANCELADO,
    TURNO_CONFIRMADO,
    TURNO_OTORGADO,
    TURNO_RECHAZADO,
    TURNO_RECORDATORIO,
    TURNO_REPROGRAMADO,
)
from app.repositories.familiar_repository import FamiliarRepository, MensajeFamiliarRepository
from app.services.familiar_service import EVENTOS_PARA_FAMILIAR, FamiliarService, texto_para_familiar
from app.utils.database import crear_indices

FECHA = datetime(2099, 11, 5, 10, 30)


def _datos(**extra):
    return {"turno_id": "t1", "paciente_id": "p1", "medico_id": "m1", "especialidad": "Cardiología", "fecha_hora": FECHA, **extra}


def _familiar(canal="sms", contacto="+5492615551234"):
    return SimpleNamespace(nombre="Marta Gómez", parentesco="Hija", canal=canal, contacto=contacto)


@pytest.fixture
def entorno():
    db = mongomock.MongoClient()["pami_test_familiar_avisos"]
    crear_indices(db)
    mensajes = MensajeFamiliarRepository(db)
    return SimpleNamespace(service=FamiliarService(FamiliarRepository(db), mensajes), mensajes=mensajes)


@pytest.mark.parametrize(
    "evento, esperado",
    [
        (TURNO_OTORGADO, "Paula tiene un turno médico otorgado para el 05/11/2099 a las 10:30 hs."),
        (TURNO_REPROGRAMADO, "El turno médico de Paula fue reprogramado para el 05/11/2099 a las 10:30 hs."),
        (TURNO_CANCELADO, "El turno médico de Paula del 05/11/2099 a las 10:30 hs fue cancelado."),
        (TURNO_CONFIRMADO, "Paula confirmó su turno médico del 05/11/2099 a las 10:30 hs."),
        (TURNO_RECORDATORIO, "Recordatorio: Paula tiene un turno médico el 05/11/2099 a las 10:30 hs."),
    ],
)
def test_el_texto_de_cada_evento(evento, esperado):
    assert texto_para_familiar(evento, "Paula Paciente", FECHA) == esperado


def test_se_usa_solo_el_nombre_de_pila():
    assert "Paciente" not in texto_para_familiar(TURNO_OTORGADO, "Paula Paciente", FECHA)


@pytest.mark.parametrize("nombre", [None, "", "   "])
def test_sin_nombre_se_usa_un_texto_generico(nombre):
    assert texto_para_familiar(TURNO_OTORGADO, nombre, FECHA).startswith("Tu familiar tiene un turno médico")


@pytest.mark.parametrize("evento", EVENTOS_PARA_FAMILIAR)
def test_el_mensaje_no_lleva_datos_clinicos(evento):
    texto = texto_para_familiar(evento, "Paula Paciente", FECHA)

    assert "Cardiología" not in texto  # la especialidad dice qué problema de salud puede tener
    assert "motivo" not in texto.lower()


def test_los_eventos_que_se_avisan():
    assert set(EVENTOS_PARA_FAMILIAR) == {TURNO_OTORGADO, TURNO_REPROGRAMADO, TURNO_CANCELADO, TURNO_CONFIRMADO, TURNO_RECORDATORIO}
    assert TURNO_RECHAZADO not in EVENTOS_PARA_FAMILIAR


def test_sin_familiar_autorizado_no_se_envia_nada(entorno):
    assert entorno.service.avisar_turno(TURNO_OTORGADO, _datos(), "Paula Paciente") is None
    assert entorno.service.listar_avisos("p1") == []


def test_con_familiar_el_aviso_queda_en_la_bandeja_de_salida(entorno):
    entorno.service.guardar("p1", _familiar())

    aviso = entorno.service.avisar_turno(TURNO_OTORGADO, _datos(), "Paula Paciente")

    assert aviso["canal"] == "sms"
    assert aviso["destino"] == "+5492615551234"
    assert aviso["evento"] == "turno.otorgado"
    assert aviso["estado"] == "enviado (simulado)"
    assert aviso["texto"] == "Paula tiene un turno médico otorgado para el 05/11/2099 a las 10:30 hs."
    assert entorno.service.listar_avisos("p1")[0]["texto"] == aviso["texto"]


def test_el_canal_elegido_arma_el_mensaje(entorno):
    entorno.service.guardar("p1", _familiar(canal="email", contacto="marta@mail.com"))

    aviso = entorno.service.avisar_turno(TURNO_CANCELADO, _datos(), "Paula Paciente")

    assert aviso["canal"] == "email"
    assert aviso["asunto"]
    assert aviso["texto"].startswith("Hola Marta Gómez:")


def test_el_aviso_va_solo_al_familiar_de_ese_paciente(entorno):
    entorno.service.guardar("p1", _familiar())

    assert entorno.service.avisar_turno(TURNO_OTORGADO, _datos(paciente_id="p2"), "Otro Paciente") is None
    assert entorno.service.listar_avisos("p2") == []


def test_despues_de_revocar_ya_no_se_envia(entorno):
    entorno.service.guardar("p1", _familiar())
    entorno.service.avisar_turno(TURNO_OTORGADO, _datos(), "Paula Paciente")
    entorno.service.revocar("p1")

    assert entorno.service.avisar_turno(TURNO_CANCELADO, _datos(), "Paula Paciente") is None
    assert len(entorno.service.listar_avisos("p1")) == 1  # lo ya enviado queda a la vista del paciente


def test_el_servicio_no_conoce_los_canales_concretos(entorno):
    # Strategy: se reemplaza el canal y el servicio funciona igual, sin ningún cambio
    class CanalFalso(CanalEnvio):
        nombre = "sms"

        def enviar(self, familiar, texto):
            return {"canal": "sms", "destino": "destino-falso", "asunto": "", "texto": f"[falso] {texto}"}

    servicio = FamiliarService(entorno.service.familiares, entorno.mensajes, canales={**CANALES, "sms": CanalFalso()})
    servicio.guardar("p1", _familiar())

    aviso = servicio.avisar_turno(TURNO_OTORGADO, _datos(), "Paula Paciente")

    assert aviso["destino"] == "destino-falso"
    assert aviso["texto"].startswith("[falso] Paula tiene")


def test_el_log_no_lleva_el_destino_ni_el_texto(entorno, caplog):
    caplog.set_level(logging.INFO)
    entorno.service.guardar("p1", _familiar())

    entorno.service.avisar_turno(TURNO_OTORGADO, _datos(), "Paula Paciente")

    assert "aviso al familiar" in caplog.text
    for dato in ("5492615551234", "Marta", "Paula", "turno médico"):
        assert dato not in caplog.text
