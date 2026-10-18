import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginSchema, RegistroPacienteSchema

VALIDO = {
    "nombre": "Juan Pérez", "email": "Juan@PamiApp.com", "telefono": "2611234567",
    "dni": "12345678", "password": "Clave12345",
}


def test_registro_valido_normaliza_email():
    assert RegistroPacienteSchema(**VALIDO).email == "juan@pamiapp.com"


def test_registro_rechaza_campo_rol():
    with pytest.raises(ValidationError):
        RegistroPacienteSchema(**VALIDO, rol="administrativo")


def test_login_rechaza_inyeccion_nosql():
    with pytest.raises(ValidationError):
        LoginSchema(email={"$ne": ""}, password={"$ne": ""})
