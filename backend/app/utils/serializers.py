OCULTOS = {"_id", "password_hash", "intentos_fallidos", "bloqueado_hasta"}


def serializar_usuario(doc: dict) -> dict:
    salida = {k: v for k, v in doc.items() if k not in OCULTOS}
    salida["id"] = str(doc["_id"])
    return salida
