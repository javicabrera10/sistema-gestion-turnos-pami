from pymongo import ASCENDING

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