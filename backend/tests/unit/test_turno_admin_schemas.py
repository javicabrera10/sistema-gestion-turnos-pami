from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.models.turno import EstadoTurno
from app.schemas.turno import FiltroTurnosSchema, OtorgarTurnoSchema

MEDICO_ID = "a" * 24


def _futuro(dias: int = 7) -> str:
    fecha = datetime.now(timezone.utc) + timedelta(days=dias)
    return fecha.replace(tzinfo=None).isoformat(timespec="seconds")


def test_otorgar_valido():
    datos = OtorgarTurnoSchema(medico_id=MEDICO_ID, fecha_hora=_futuro())
    assert datos.medico_id == MEDICO_ID
    assert datos.fecha_hora.tzinfo is None


@pytest.mark.parametrize("medico_id", ["123", "z" * 24, "a" * 25, {"$ne": ""}])
def test_otorgar_rechaza_medico_id_mal_formado(medico_id):
    with pytest.raises(ValidationError):
        OtorgarTurnoSchema(medico_id=medico_id, fecha_hora=_futuro())


def test_otorgar_rechaza_fecha_pasada():
    with pytest.raises(ValidationError):
        OtorgarTurnoSchema(medico_id=MEDICO_ID, fecha_hora="2020-01-01T10:00:00")


@pytest.mark.parametrize("campo", ["estado", "administrativo_id", "paciente_id"])
def test_otorgar_rechaza_campos_que_no_manda_el_cliente(campo):
    with pytest.raises(ValidationError):
        OtorgarTurnoSchema(medico_id=MEDICO_ID, fecha_hora=_futuro(), **{campo: "x"})


@pytest.mark.parametrize("campo", ["medico_id", "fecha_hora"])
def test_otorgar_rechaza_si_falta_un_campo(campo):
    datos = {"medico_id": MEDICO_ID, "fecha_hora": _futuro()}
    datos.pop(campo)
    with pytest.raises(ValidationError):
        OtorgarTurnoSchema(**datos)


def test_filtro_sin_estado():
    assert FiltroTurnosSchema.model_validate({}).estado is None


def test_filtro_con_estado():
    filtro = FiltroTurnosSchema.model_validate({"estado": "solicitado"})
    assert filtro.estado == EstadoTurno.SOLICITADO


@pytest.mark.parametrize("params", [{"estado": "inventado"}, {"otro": "x"}])
def test_filtro_rechaza_valores_invalidos(params):
    with pytest.raises(ValidationError):
        FiltroTurnosSchema.model_validate(params)
