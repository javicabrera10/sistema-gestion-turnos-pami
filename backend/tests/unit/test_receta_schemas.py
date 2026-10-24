import pytest
from pydantic import ValidationError

from app.schemas.receta import PlanSchema, RecetaCrearSchema, RecetaEditarSchema

PACIENTE = "a" * 24
IBUPROFENO = {"nombre": "Ibuprofeno", "dosis": "400 mg", "horario_toma": "Cada 8 horas"}
ITEM_PLAN = {"medicamento": "Ibuprofeno", "dosis": "400 mg", "horarios": ["08:00", "16:00"], "duracion_dias": 7}


def test_receta_valida():
    r = RecetaCrearSchema.model_validate({"paciente_id": PACIENTE, "medicamentos": [IBUPROFENO]})
    assert r.tipo == "receta"
    assert r.medicamentos[0].nombre == "Ibuprofeno"


def test_receta_sin_medicamentos_falla():
    with pytest.raises(ValidationError):
        RecetaCrearSchema.model_validate({"paciente_id": PACIENTE, "medicamentos": []})


def test_receta_sin_el_campo_medicamentos_falla():
    with pytest.raises(ValidationError):
        RecetaCrearSchema.model_validate({"paciente_id": PACIENTE})


def test_orden_no_necesita_medicamentos():
    r = RecetaCrearSchema.model_validate(
        {"tipo": "orden", "paciente_id": PACIENTE, "indicaciones": "Radiografía de rodilla"}
    )
    assert r.tipo == "orden"
    assert r.medicamentos == []


def test_orden_sin_indicaciones_falla():
    with pytest.raises(ValidationError):
        RecetaCrearSchema.model_validate({"tipo": "orden", "paciente_id": PACIENTE})


def test_orden_con_medicamentos_falla():
    with pytest.raises(ValidationError):
        RecetaCrearSchema.model_validate(
            {"tipo": "orden", "paciente_id": PACIENTE, "indicaciones": "Radiografía", "medicamentos": [IBUPROFENO]}
        )


@pytest.mark.parametrize("extra", [{"medico_id": "b" * 24}, {"estado": "emitida"}, {"fecha": "2099-01-01"}])
def test_el_cliente_no_puede_mandar_campos_internos(extra):
    with pytest.raises(ValidationError):
        RecetaCrearSchema.model_validate({"paciente_id": PACIENTE, "medicamentos": [IBUPROFENO], **extra})


@pytest.mark.parametrize("paciente_id", ["", "123", "z" * 24, "a" * 25])
def test_paciente_id_debe_ser_un_id_valido(paciente_id):
    with pytest.raises(ValidationError):
        RecetaCrearSchema.model_validate({"paciente_id": paciente_id, "medicamentos": [IBUPROFENO]})


def test_tipo_invalido_falla():
    with pytest.raises(ValidationError):
        RecetaCrearSchema.model_validate({"tipo": "certificado", "paciente_id": PACIENTE, "medicamentos": [IBUPROFENO]})


def test_editar_necesita_algo_para_cambiar():
    with pytest.raises(ValidationError):
        RecetaEditarSchema.model_validate({})


@pytest.mark.parametrize("cuerpo", [{"paciente_id": "a" * 24}, {"tipo": "orden"}, {"estado": "emitida"}])
def test_editar_no_permite_cambiar_paciente_tipo_ni_estado(cuerpo):
    with pytest.raises(ValidationError):
        RecetaEditarSchema.model_validate({"indicaciones": "Tomar con agua", **cuerpo})


def test_plan_valido():
    assert PlanSchema.model_validate({"plan": [ITEM_PLAN]}).plan[0].duracion_dias == 7


@pytest.mark.parametrize("horario", ["25:00", "8:00", "08:60", "mañana", ""])
def test_plan_rechaza_horarios_invalidos(horario):
    with pytest.raises(ValidationError):
        PlanSchema.model_validate({"plan": [{**ITEM_PLAN, "horarios": [horario]}]})


@pytest.mark.parametrize("dias", [0, -1, 366])
def test_plan_rechaza_duraciones_invalidas(dias):
    with pytest.raises(ValidationError):
        PlanSchema.model_validate({"plan": [{**ITEM_PLAN, "duracion_dias": dias}]})


def test_plan_no_puede_estar_vacio():
    with pytest.raises(ValidationError):
        PlanSchema.model_validate({"plan": []})
