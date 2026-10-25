import os
from datetime import timedelta


def lista_desde_env(nombre, por_defecto):
    """Lee una lista separada por comas desde una variable de entorno (o usa el valor por defecto)."""
    items = [x.strip() for x in os.getenv(nombre, "").split(",") if x.strip()]
    return items or list(por_defecto)


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
    MONGO_DB = os.getenv("MONGO_DB", "pami_db")
    CORS_ORIGINS = lista_desde_env("CORS_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"])
    RATELIMIT_STORAGE_URI = "memory://"


class TestConfig(Config):
    TESTING = True
    MONGO_DB = "pami_test_db"
    CORS_ORIGINS = ["http://localhost:5173"]
    SECRET_KEY = "clave-de-pruebas-solo-para-tests-1234567890"
    JWT_SECRET_KEY = "jwt-de-pruebas-solo-para-tests-1234567890"


def validar_configuracion(app):
    """La app no arranca si faltan las claves secretas (nunca van escritas en el código)."""
    faltan = [c for c in ("SECRET_KEY", "JWT_SECRET_KEY") if not app.config.get(c)]
    if faltan:
        raise RuntimeError(
            "Falta configurar: " + ", ".join(faltan) + ". Definilas en el archivo .env (ver .env.example)."
        )