import pytest

from app.patterns.canal_strategy import (
    CANALES,
    LARGO_MAXIMO_SMS,
    CanalEmail,
    CanalEnvio,
    CanalSMS,
    canal_por_nombre,
)

SMS = {"nombre": "Marta Gómez", "canal": "sms", "contacto": "+5492615551234"}
EMAIL = {"nombre": "Marta Gómez", "canal": "email", "contacto": "marta@mail.com"}


def test_el_sms_va_al_telefono_y_no_lleva_asunto():
    entrega = CanalSMS().enviar(SMS, "Paula tiene un turno médico.")

    assert entrega == {"canal": "sms", "destino": "+5492615551234", "asunto": "", "texto": "Paula tiene un turno médico."}


def test_el_sms_se_corta_en_160_caracteres():
    entrega = CanalSMS().enviar(SMS, "a" * 400)

    assert len(entrega["texto"]) == LARGO_MAXIMO_SMS
    assert entrega["texto"].endswith("…")


def test_un_sms_corto_no_se_modifica():
    texto = "a" * LARGO_MAXIMO_SMS

    assert CanalSMS().enviar(SMS, texto)["texto"] == texto


def test_el_email_lleva_asunto_saludo_y_aclaracion():
    entrega = CanalEmail().enviar(EMAIL, "Paula tiene un turno médico.")

    assert entrega["canal"] == "email"
    assert entrega["destino"] == "marta@mail.com"
    assert entrega["asunto"] == CanalEmail.ASUNTO
    assert entrega["texto"].startswith("Hola Marta Gómez:")
    assert "Paula tiene un turno médico." in entrega["texto"]
    assert CanalEmail.ACLARACION in entrega["texto"]


def test_el_email_no_se_corta():
    assert "a" * 400 in CanalEmail().enviar(EMAIL, "a" * 400)["texto"]


@pytest.mark.parametrize("canal, familiar", [(CanalSMS(), SMS), (CanalEmail(), EMAIL)])
def test_los_canales_son_intercambiables(canal, familiar):
    # quien usa un canal solo conoce la interfaz: le pasa el familiar y el texto y recibe la entrega
    assert isinstance(canal, CanalEnvio)
    entrega = canal.enviar(familiar, "Hola")

    assert set(entrega) == {"canal", "destino", "asunto", "texto"}
    assert entrega["canal"] == canal.nombre
    assert entrega["destino"] == familiar["contacto"]


def test_no_se_puede_instanciar_la_interfaz():
    with pytest.raises(TypeError):
        CanalEnvio()


def test_se_elige_el_canal_por_nombre():
    assert isinstance(canal_por_nombre("sms"), CanalSMS)
    assert isinstance(canal_por_nombre("email"), CanalEmail)
    assert set(CANALES) == {"sms", "email"}


def test_un_canal_desconocido_falla_con_un_mensaje_claro():
    with pytest.raises(ValueError, match="whatsapp"):
        canal_por_nombre("whatsapp")


def test_se_puede_sumar_un_canal_propio_sin_tocar_el_resto():
    class CanalWhatsApp(CanalEnvio):
        nombre = "whatsapp"

        def enviar(self, familiar, texto):
            return {"canal": self.nombre, "destino": familiar["contacto"], "asunto": "", "texto": f"💬 {texto}"}

    canales = {**CANALES, "whatsapp": CanalWhatsApp()}
    entrega = canal_por_nombre("whatsapp", canales).enviar(SMS, "Hola")

    assert entrega["texto"] == "💬 Hola"
