OCULTOS = {"_id", "password_hash", "intentos_fallidos", "bloqueado_hasta"}


def serializar_usuario(doc: dict) -> dict:
    salida = {k: v for k, v in doc.items() if k not in OCULTOS}
    salida["id"] = str(doc["_id"])
    return salida


def serializar_turno(doc: dict) -> dict:
    salida = {k: v for k, v in doc.items() if k != "_id"}
    salida["id"] = str(doc["_id"])
    salida["fecha_hora"] = doc["fecha_hora"].isoformat()
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
