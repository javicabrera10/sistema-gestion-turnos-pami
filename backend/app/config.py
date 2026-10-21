import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
    MONGO_DB = os.getenv("MONGO_DB", "pami_db")
    CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
    RATELIMIT_STORAGE_URI = "memory://"


class TestConfig(Config):
    TESTING = True
    MONGO_DB = "pami_test_db"
    SECRET_KEY = "clave-de-pruebas-solo-para-tests-1234567890"
    JWT_SECRET_KEY = "jwt-de-pruebas-solo-para-tests-1234567890"
