import pytest
from pydantic import ValidationError

from app.schemas.preferencias import PreferenciasSchema

VALIDO = {"tamano_letra": "grande", "alto_contraste": True, "voz_activada": False}


def test_preferencias_validas():
    p = PreferenciasSchema(**VALIDO)
    assert p.tamano_letra == "grande"
    assert p.alto_contraste is True
    assert p.voz_activada is False


@pytest.mark.parametrize("tamano", ["enorme", "", "GRANDE", 3, None])
def test_rechaza_tamano_de_letra_invalido(tamano):
    with pytest.raises(ValidationError):
        PreferenciasSchema(**{**VALIDO, "tamano_letra": tamano})


@pytest.mark.parametrize("campo", ["alto_contraste", "voz_activada"])
@pytest.mark.parametrize("valor", ["si", "true", 1, None])
def test_rechaza_valores_que_no_son_booleanos(campo, valor):
    with pytest.raises(ValidationError):
        PreferenciasSchema(**{**VALIDO, campo: valor})


def test_rechaza_campos_de_mas():
    with pytest.raises(ValidationError):
        PreferenciasSchema(**VALIDO, usuario_id="123")


def test_rechaza_si_falta_un_campo():
    with pytest.raises(ValidationError):
        PreferenciasSchema(tamano_letra="normal", alto_contraste=False)