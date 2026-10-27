"""Patrón Strategy: canales de envío intercambiables para avisarle al familiar autorizado.

Cada canal sabe cómo armar el mensaje que le llega al familiar (largo, asunto, texto). El servicio
de familiares elige el canal que el paciente indicó y lo usa sin saber cuál es: sumar un canal nuevo
(por ejemplo WhatsApp) es crear otra clase con la misma interfaz, sin tocar el servicio.

En este proyecto el envío es SIMULADO: el canal devuelve el mensaje tal como saldría y el servicio lo
deja en la bandeja de salida del paciente. Con un proveedor real, el mismo método llamaría a su API.

Canales disponibles:
    "sms"    mensaje corto, de hasta 160 caracteres, sin asunto
    "email"  mensaje con asunto y una aclaración de por qué se lo recibe
"""

from abc import ABC, abstractmethod

LARGO_MAXIMO_SMS = 160


class CanalEnvio(ABC):
    # Es el valor que el paciente elige en el campo "canal" y que se guarda con el familiar
    nombre: str

    @abstractmethod
    def enviar(self, familiar: dict, texto: str) -> dict:
        """Devuelve la entrega: {"canal", "destino", "asunto", "texto"}. No guarda nada ni conoce la base."""


class CanalSMS(CanalEnvio):
    nombre = "sms"

    def enviar(self, familiar: dict, texto: str) -> dict:
        # un SMS no puede pasar de 160 caracteres: si el texto es más largo se corta con "…"
        if len(texto) > LARGO_MAXIMO_SMS:
            texto = texto[: LARGO_MAXIMO_SMS - 1] + "…"
        return {"canal": self.nombre, "destino": familiar["contacto"], "asunto": "", "texto": texto}


class CanalEmail(CanalEnvio):
    nombre = "email"
    ASUNTO = "Aviso de turno médico - App PAMI"
    ACLARACION = "Recibís este aviso porque el paciente te autorizó. Si no querés recibirlo, pedile que lo desactive."

    def enviar(self, familiar: dict, texto: str) -> dict:
        cuerpo = f"Hola {familiar['nombre']}:\n\n{texto}\n\n{self.ACLARACION}"
        return {"canal": self.nombre, "destino": familiar["contacto"], "asunto": self.ASUNTO, "texto": cuerpo}


CANALES = {canal.nombre: canal for canal in (CanalSMS(), CanalEmail())}


def canal_por_nombre(nombre: str, canales=None) -> CanalEnvio:
    canales = CANALES if canales is None else canales
    if nombre not in canales:
        raise ValueError(f"Canal de envío desconocido: {nombre!r}")
    return canales[nombre]
