from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.config import lista_desde_env, validar_configuracion
from app.schemas.auth import LoginSchema, RegistroPacienteSchema

VALIDO = {
    "nombre": "Juan Pérez", "email": "juan@pamiapp.com", "telefono": "2611234567",
    "dni": "12345678", "password": "Clave12345",
}


@pytest.mark.parametrize("password", ["clave12345", "CLAVE12345", "ClaveSinNumero", "Ab1"])
def test_registro_rechaza_contrasenas_debiles(password):
    with pytest.raises(ValidationError):
        RegistroPacienteSchema(**{**VALIDO, "password": password})


def test_registro_acepta_contrasena_con_mayuscula_minuscula_y_numero():
    assert RegistroPacienteSchema(**VALIDO).password == "Clave12345"


def test_login_no_exige_complejidad():
    assert LoginSchema(email="a@b.com", password="x").password == "x"


def test_cors_lee_la_lista_de_la_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", " http://a.com , http://b.com ,,")
    assert lista_desde_env("CORS_ORIGINS", ["http://por-defecto.com"]) == ["http://a.com", "http://b.com"]


@pytest.mark.parametrize("valor", [None, "", "  ,  "])
def test_cors_usa_el_valor_por_defecto_si_no_hay_variable(monkeypatch, valor):
    if valor is None:
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
    else:
        monkeypatch.setenv("CORS_ORIGINS", valor)
    assert lista_desde_env("CORS_ORIGINS", ["http://por-defecto.com"]) == ["http://por-defecto.com"]


def _app(**config):
    return SimpleNamespace(config=config)


def test_validar_configuracion_acepta_ambas_claves():
    validar_configuracion(_app(SECRET_KEY="a", JWT_SECRET_KEY="b"))


def test_validar_configuracion_falta_secret_key():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        validar_configuracion(_app(SECRET_KEY=None, JWT_SECRET_KEY="b"))


def test_validar_configuracion_falta_jwt_secret_key():
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        validar_configuracion(_app(SECRET_KEY="a", JWT_SECRET_KEY=""))