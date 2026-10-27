import pytest
from pydantic import ValidationError

from app.schemas.familiar import FamiliarSchema


def _datos(**cambios):
    base = {
        "nombre": "Marta Gómez",
        "parentesco": "Hija",
        "canal": "sms",
        "contacto": "+54 9 261 555-1234",
        "consentimiento": True,
    }
    return {**base, **cambios}


def test_datos_validos_con_sms_normalizan_el_telefono():
    datos = FamiliarSchema.model_validate(_datos())

    assert datos.contacto == "+5492615551234"
    assert datos.canal == "sms"


def test_datos_validos_con_email_lo_pasan_a_minusculas():
    datos = FamiliarSchema.model_validate(_datos(canal="email", contacto="Marta.Gomez@Mail.com"))

    assert datos.contacto == "marta.gomez@mail.com"


def test_se_recortan_los_espacios_de_los_textos():
    datos = FamiliarSchema.model_validate(_datos(nombre="  Marta Gómez  ", parentesco=" Hija "))

    assert (datos.nombre, datos.parentesco) == ("Marta Gómez", "Hija")


@pytest.mark.parametrize("consentimiento", [False, None, "si", "true", 1, 0, "", []])
def test_sin_consentimiento_explicito_no_se_acepta(consentimiento):
    with pytest.raises(ValidationError):
        FamiliarSchema.model_validate(_datos(consentimiento=consentimiento))


def test_el_consentimiento_es_obligatorio():
    datos = _datos()
    del datos["consentimiento"]

    with pytest.raises(ValidationError):
        FamiliarSchema.model_validate(datos)


@pytest.mark.parametrize("contacto", ["no-es-un-email", "marta@", "@mail.com", "marta@mail", "12345678"])
def test_email_invalido(contacto):
    with pytest.raises(ValidationError):
        FamiliarSchema.model_validate(_datos(canal="email", contacto=contacto))


@pytest.mark.parametrize("contacto", ["abc", "123", "26155a1234", "marta@mail.com", "+" * 10, "1" * 16])
def test_telefono_invalido(contacto):
    with pytest.raises(ValidationError):
        FamiliarSchema.model_validate(_datos(canal="sms", contacto=contacto))


@pytest.mark.parametrize("canal", ["whatsapp", "", None, "SMS"])
def test_el_canal_tiene_que_ser_sms_o_email(canal):
    with pytest.raises(ValidationError):
        FamiliarSchema.model_validate(_datos(canal=canal))


@pytest.mark.parametrize("campo, valor", [("nombre", "M"), ("nombre", "M" * 81), ("parentesco", "H"), ("parentesco", "H" * 41)])
def test_largos_de_nombre_y_parentesco(campo, valor):
    with pytest.raises(ValidationError):
        FamiliarSchema.model_validate(_datos(**{campo: valor}))


@pytest.mark.parametrize("extra", [{"paciente_id": "otro"}, {"rol": "administrativo"}, {"$set": {"x": 1}}])
def test_no_acepta_campos_extra(extra):
    with pytest.raises(ValidationError):
        FamiliarSchema.model_validate(_datos(**extra))


@pytest.mark.parametrize("contacto", [{"$ne": ""}, ["+5492615551234"], 5492615551234, None])
def test_el_contacto_tiene_que_ser_texto(contacto):
    with pytest.raises(ValidationError):
        FamiliarSchema.model_validate(_datos(contacto=contacto))
