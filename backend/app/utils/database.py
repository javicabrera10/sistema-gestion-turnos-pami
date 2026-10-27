from pymongo import ASCENDING, DESCENDING

from app.security.passwords import hash_password

USUARIOS_DEMO = [
    {"nombre": "Ana Administrativa", "email": "admin@pamiapp.com", "telefono": "2610000001",
     "rol": "administrativo", "legajo": "A-001", "password": "Admin1234"},
    {"nombre": "Martín Médico", "email": "medico@pamiapp.com", "telefono": "2610000002",
     "rol": "medico", "matricula": "MP-1234", "especialidad": "Clínica médica", "password": "Medico1234"},
    {"nombre": "Paula Paciente", "email": "paciente@pamiapp.com", "telefono": "2610000003",
     "rol": "paciente", "dni": "30111222", "historia_clinica": "", "password": "Paciente1234"},
]


def crear_indices(db) -> None:
    db.usuarios.create_index([("email", ASCENDING)], unique=True, name="uq_usuarios_email")
    db.turnos.create_index(
        [("paciente_id", ASCENDING), ("fecha_hora", ASCENDING)], name="ix_turnos_paciente_fecha"
    )
    db.turnos.create_index(
        [("medico_id", ASCENDING), ("fecha_hora", ASCENDING)], name="ix_turnos_medico_fecha"
    )
    db.recetas.create_index([("medico_id", ASCENDING)], name="ix_recetas_medico")
    db.recetas.create_index([("paciente_id", ASCENDING), ("estado", ASCENDING)], name="ix_recetas_paciente_estado")
    db.notificaciones.create_index(
        [("destinatario_id", ASCENDING), ("creada_en", DESCENDING)], name="ix_notificaciones_destinatario"
    )
    # un solo familiar autorizado por paciente, y su bandeja de avisos enviados
    db.familiares_autorizados.create_index([("paciente_id", ASCENDING)], unique=True, name="uq_familiar_paciente")
    db.mensajes_familiar.create_index(
        [("paciente_id", ASCENDING), ("creado_en", DESCENDING)], name="ix_mensajes_familiar_paciente"
    )
    # un aviso de toma por receta, día, medicamento y horario
    db.avisos_toma.create_index(
        [("receta_id", ASCENDING), ("dia", ASCENDING), ("medicamento", ASCENDING), ("horario", ASCENDING)],
        unique=True,
        name="uq_avisos_toma",
    )


def seed_usuarios(db) -> int:
    creados = 0
    for datos in USUARIOS_DEMO:
        if db.usuarios.find_one({"email": datos["email"]}):
            continue
        doc = {k: v for k, v in datos.items() if k != "password"}
        doc["password_hash"] = hash_password(datos["password"])
        doc["intentos_fallidos"] = 0
        doc["bloqueado_hasta"] = None
        db.usuarios.insert_one(doc)
        creados += 1
    return creados