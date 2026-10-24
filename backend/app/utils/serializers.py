OCULTOS = {"_id", "password_hash", "intentos_fallidos", "bloqueado_hasta"}


def _iso(valor):
    """datetime -> texto ISO; cualquier otro valor se deja igual."""
    return valor.isoformat() if hasattr(valor, "isoformat") else valor


def serializar_usuario(doc: dict) -> dict:
    salida = {k: v for k, v in doc.items() if k not in OCULTOS}
    salida["id"] = str(doc["_id"])
    return salida


def serializar_turno(doc: dict) -> dict:
    salida = {k: v for k, v in doc.items() if k != "_id"}
    salida["id"] = str(doc["_id"])
    salida["fecha_hora"] = _iso(doc["fecha_hora"])
    if "creado_en" in salida:
        salida["creado_en"] = _iso(salida["creado_en"])
    return salida

def serializar_turno_con_paciente(doc: dict) -> dict:
    """Turno + datos de contacto del paciente (para el administrativo)."""
    paciente = doc.get("paciente")
    salida = serializar_turno({k: v for k, v in doc.items() if k != "paciente"})
    salida["paciente"] = None if paciente is None else {
        "id": str(paciente["_id"]),
        "nombre": paciente["nombre"],
        "dni": paciente.get("dni", ""),
        "telefono": paciente["telefono"],
    }
    return salida


def serializar_notificacion(doc: dict) -> dict:
    salida = {k: v for k, v in doc.items() if k != "_id"}
    salida["id"] = str(doc["_id"])
    salida["creada_en"] = _iso(doc["creada_en"])
    return salida


def serializar_receta(doc: dict) -> dict:
    salida = {k: v for k, v in doc.items() if k != "_id"}
    salida["id"] = str(doc["_id"])
    salida["fecha"] = _iso(doc["fecha"])
    return salida
