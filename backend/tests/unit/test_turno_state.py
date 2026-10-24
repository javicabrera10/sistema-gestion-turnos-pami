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


# ---------- Sprint 2: reprogramar y cancelar ----------

@pytest.mark.parametrize("estado", [EstadoTurno.OTORGADO, EstadoTurno.CONFIRMADO, EstadoTurno.REPROGRAMADO])
def test_se_puede_reprogramar_y_cancelar_un_turno_activo(estado):
    assert estado_de(estado).reprogramar() == EstadoTurno.REPROGRAMADO
    assert estado_de(estado).cancelar() == EstadoTurno.CANCELADO


def test_el_paciente_responde_a_un_turno_reprogramado():
    assert estado_de(EstadoTurno.REPROGRAMADO).confirmar() == EstadoTurno.CONFIRMADO
    assert estado_de(EstadoTurno.REPROGRAMADO).rechazar() == EstadoTurno.RECHAZADO


@pytest.mark.parametrize(
    "estado",
    [EstadoTurno.SOLICITADO, EstadoTurno.RECHAZADO, EstadoTurno.CANCELADO],
)
@pytest.mark.parametrize("accion", ["reprogramar", "cancelar"])
def test_no_se_reprograma_ni_cancela_un_turno_sin_otorgar_o_terminado(estado, accion):
    with pytest.raises(TransicionInvalida):
        getattr(estado_de(estado), accion)()
