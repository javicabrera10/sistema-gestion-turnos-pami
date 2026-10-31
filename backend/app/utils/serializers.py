OCULTOS = {"_id", "password_hash", "intentos_fallidos", "bloqueado_hasta"}


def _iso(valor):
    """datetime -> texto ISO; cualquier otro valor se deja igual."""
    return valor.isoformat() if hasattr(valor, "isoformat") else valor


def serializar_usuario(doc: dict) -> dict:
    salida = {k: v for k, v in doc.items() if k not in OCULTOS}
    salida["id"] = str(doc["_id"])
    return salida


# campos internos que no se muestran en la API
OCULTOS_TURNO = {"_id", "recordatorios_enviados"}


def serializar_turno(doc: dict) -> dict:
    salida = {k: v for k, v in doc.items() if k not in OCULTOS_TURNO}
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


def serializar_familiar(doc: dict) -> dict:
    salida = {k: v for k, v in doc.items() if k != "_id"}
    salida["id"] = str(doc["_id"])
    salida["autorizado_en"] = _iso(doc["autorizado_en"])
    return salida


def serializar_mensaje_familiar(doc: dict) -> dict:
    salida = {k: v for k, v in doc.items() if k != "_id"}
    salida["id"] = str(doc["_id"])
    salida["creado_en"] = _iso(doc["creado_en"])
    return salida


def serializar_receta(doc: dict) -> dict:
    salida = {k: v for k, v in doc.items() if k != "_id"}
    salida["id"] = str(doc["_id"])
    salida["fecha"] = _iso(doc["fecha"])
    for campo in ("inicio_plan", "recordatorio_generado_en"):
        if campo in salida:
            salida[campo] = _iso(salida[campo])
    return salida


def serializar_receta_para_administrativo(doc: dict) -> dict:
    """Receta emitida + datos del paciente y del médico, para el administrativo.

    No lleva medicamentos, dosis ni indicaciones: son datos de salud y al administrativo
    le alcanza con saber de quién es la receta y si ya se generó su recordatorio.
    """
    paciente, medico = doc.get("paciente"), doc.get("medico")
    return {
        "id": str(doc["_id"]),
        "tipo": doc["tipo"],
        "fecha": _iso(doc["fecha"]),
        "con_plan": bool(doc.get("plan_medicacion")),
        "recordatorio_generado_en": _iso(doc.get("recordatorio_generado_en")),
        "paciente": None
        if paciente is None
        else {
            "id": str(paciente["_id"]),
            "nombre": paciente["nombre"],
            "dni": paciente.get("dni", ""),
            "telefono": paciente.get("telefono", ""),
        },
        "medico": None
        if medico is None
        else {"id": str(medico["_id"]), "nombre": medico["nombre"], "especialidad": medico.get("especialidad", "")},
    }
