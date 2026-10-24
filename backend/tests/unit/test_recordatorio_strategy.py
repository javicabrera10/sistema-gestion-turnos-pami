from datetime import datetime, timedelta

import pytest

from app.patterns.recordatorio_strategy import (
    REGLAS_POR_DEFECTO,
    Recordar2Horas,
    Recordar24Horas,
    ReglaRecordatorio,
    reglas_desde_nombres,
)

AHORA = datetime(2099, 5, 10, 8, 0)


def _en(**tiempo) -> datetime:
    return AHORA + timedelta(**tiempo)


@pytest.mark.parametrize(
    "faltan, esperado",
    [
        (timedelta(hours=23), True),
        (timedelta(hours=24), True),  # justo 24 horas: ya corresponde
        (timedelta(hours=24, minutes=1), False),
        (timedelta(minutes=1), True),
        (timedelta(0), False),  # el turno es ahora: ya no es un recordatorio
        (timedelta(hours=-1), False),  # turno pasado
    ],
)
def test_regla_de_24_horas(faltan, esperado):
    assert Recordar24Horas().debe_recordar(AHORA + faltan, AHORA) is esperado


@pytest.mark.parametrize(
    "faltan, esperado",
    [
        (timedelta(minutes=90), True),
        (timedelta(hours=2), True),
        (timedelta(hours=2, minutes=1), False),
        (timedelta(hours=20), False),
        (timedelta(hours=-1), False),
    ],
)
def test_regla_de_2_horas(faltan, esperado):
    assert Recordar2Horas().debe_recordar(AHORA + faltan, AHORA) is esperado


@pytest.mark.parametrize("regla", [Recordar24Horas(), Recordar2Horas()])
def test_las_reglas_son_intercambiables(regla):
    # el que usa una regla solo conoce la interfaz, no la clase concreta
    assert isinstance(regla, ReglaRecordatorio)
    assert isinstance(regla.nombre, str) and regla.horas_antes > 0
    assert regla.debe_recordar(_en(minutes=30), AHORA) is True


def test_no_se_puede_instanciar_la_interfaz():
    with pytest.raises(TypeError):
        ReglaRecordatorio()


def test_las_reglas_por_defecto_van_de_la_mas_urgente_a_la_menos_urgente():
    assert [r.nombre for r in REGLAS_POR_DEFECTO] == ["2h", "24h"]


def test_se_eligen_las_reglas_por_nombre_y_quedan_ordenadas():
    reglas = reglas_desde_nombres(" 24h , 2h ")
    assert [type(r) for r in reglas] == [Recordar2Horas, Recordar24Horas]
    assert [r.nombre for r in reglas_desde_nombres("24h")] == ["24h"]
    assert reglas_desde_nombres("") == ()


def test_regla_desconocida():
    with pytest.raises(ValueError):
        reglas_desde_nombres("24h,1semana")
