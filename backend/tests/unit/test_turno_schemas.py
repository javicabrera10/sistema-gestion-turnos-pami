from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.schemas.turno import SolicitudTurnoSchema


def _futuro(dias: int = 7) -> str:
    fecha = datetime.now(timezone.utc) + timedelta(days=dias)
    return fecha.replace(tzinfo=None).isoformat(timespec="seconds")


def _valido(**cambios) -> dict:
    datos = {"especialidad": "Cardiología", "fecha_hora": _futuro(), "motivo": "Control anual"}
    return {**datos, **cambios}


def test_solicitud_valida():
    datos = SolicitudTurnoSchema(**_valido())
    assert datos.especialidad == "Cardiología"
    assert isinstance(datos.fecha_hora, datetime)
    assert datos.fecha_hora.tzinfo is None


def test_recorta_espacios():
    datos = SolicitudTurnoSchema(**_valido(especialidad="  Cardiología  ", motivo="  Control  "))
    assert datos.especialidad == "Cardiología"
    assert datos.motivo == "Control"


def test_rechaza_fecha_pasada():
    with pytest.raises(ValidationError):
        SolicitudTurnoSchema(**_valido(fecha_hora="2020-01-01T10:00:00"))


def test_fecha_con_zona_horaria_se_pasa_a_utc():
    datos = SolicitudTurnoSchema(**_valido(fecha_hora="2099-01-01T10:00:00-03:00"))
    assert datos.fecha_hora == datetime(2099, 1, 1, 13, 0)


@pytest.mark.parametrize("campo", ["estado", "paciente_id", "medico_id", "administrativo_id"])
def test_rechaza_campos_que_no_manda_el_cliente(campo):
    with pytest.raises(ValidationError):
        SolicitudTurnoSchema(**_valido(**{campo: "x"}))


def test_rechaza_inyeccion_nosql():
    with pytest.raises(ValidationError):
        SolicitudTurnoSchema(**_valido(especialidad={"$ne": ""}))


@pytest.mark.parametrize("campo", ["especialidad", "fecha_hora", "motivo"])
def test_rechaza_si_falta_un_campo(campo):
    datos = _valido()
    datos.pop(campo)
    with pytest.raises(ValidationError):
        SolicitudTurnoSchema(**datos)


def test_rechaza_especialidad_muy_corta():
    with pytest.raises(ValidationError):
        SolicitudTurnoSchema(**_valido(especialidad="ab"))
