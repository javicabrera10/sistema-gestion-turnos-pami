import pytest

from app.models.turno import EstadoTurno
from app.patterns.turno_state import TransicionInvalida, estado_de


def test_solicitado_puede_otorgarse():
    assert estado_de(EstadoTurno.SOLICITADO).otorgar() == EstadoTurno.OTORGADO


def test_otorgado_puede_confirmarse():
    assert estado_de(EstadoTurno.OTORGADO).confirmar() == EstadoTurno.CONFIRMADO


def test_otorgado_puede_rechazarse():
    assert estado_de(EstadoTurno.OTORGADO).rechazar() == EstadoTurno.RECHAZADO


def test_estado_de_acepta_el_texto_guardado_en_mongo():
    assert estado_de("otorgado").confirmar() == EstadoTurno.CONFIRMADO


def test_todos_los_estados_tienen_su_clase():
    for e in EstadoTurno:
        assert estado_de(e).estado == e


@pytest.mark.parametrize(
    "estado, accion",
    [
        (EstadoTurno.SOLICITADO, "confirmar"),
        (EstadoTurno.SOLICITADO, "rechazar"),
        (EstadoTurno.OTORGADO, "otorgar"),
        (EstadoTurno.CONFIRMADO, "confirmar"),
        (EstadoTurno.CONFIRMADO, "rechazar"),
        (EstadoTurno.RECHAZADO, "confirmar"),
        (EstadoTurno.CANCELADO, "otorgar"),
    ],
)
def test_transiciones_invalidas(estado, accion):
    with pytest.raises(TransicionInvalida):
        getattr(estado_de(estado), accion)()


def test_estado_desconocido():
    with pytest.raises(ValueError):
        estado_de("inventado")
