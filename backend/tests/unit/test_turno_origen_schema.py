import pytest
from pydantic import ValidationError

from app.schemas.turno import FiltroMedicosSchema, RespuestaTurnoSchema, SolicitudTurnoSchema

BASE = {"especialidad": "Cardiología", "fecha_hora": "2099-01-01T10:00:00", "motivo": "Control anual"}


def test_el_origen_por_defecto_es_manual():
    assert SolicitudTurnoSchema.model_validate(BASE).origen == "manual"


@pytest.mark.parametrize("origen", ["manual", "voz"])
def test_acepta_origen_manual_y_voz(origen):
    assert SolicitudTurnoSchema.model_validate({**BASE, "origen": origen}).origen == origen


@pytest.mark.parametrize("origen", ["telepatia", "", "VOZ", None])
def test_rechaza_origen_invalido(origen):
    with pytest.raises(ValidationError):
        SolicitudTurnoSchema.model_validate({**BASE, "origen": origen})


@pytest.mark.parametrize("accion", ["aceptar", "rechazar"])
def test_respuesta_acepta_aceptar_y_rechazar(accion):
    assert RespuestaTurnoSchema.model_validate({"accion": accion}).accion == accion


@pytest.mark.parametrize("cuerpo", [{"accion": "quizas"}, {}, {"accion": "aceptar", "estado": "confirmado"}])
def test_respuesta_rechaza_accion_invalida_y_campos_extra(cuerpo):
    with pytest.raises(ValidationError):
        RespuestaTurnoSchema.model_validate(cuerpo)


def test_filtro_de_medicos_rechaza_campos_extra():
    with pytest.raises(ValidationError):
        FiltroMedicosSchema.model_validate({"rol": "paciente"})
