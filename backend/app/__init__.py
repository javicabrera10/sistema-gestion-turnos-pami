from flask import Flask, jsonify
from flask_cors import CORS
from pydantic import ValidationError
from pymongo import MongoClient

from .config import Config
from .extensions import jwt, limiter, swagger


def create_app(config_class=Config, db=None):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app, origins=app.config["CORS_ORIGINS"])
    jwt.init_app(app)
    limiter.init_app(app)
    swagger.init_app(app)

    if db is None:
        client = MongoClient(app.config["MONGO_URI"], serverSelectionTimeoutMS=3000)
        db = client[app.config["MONGO_DB"]]
    app.db = db

    from .routes.auth import auth_bp
    from .routes.health import health_bp
    from .routes.usuarios import usuarios_bp
    from .routes.turnos import turnos_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(usuarios_bp, url_prefix="/api/usuarios")
    app.register_blueprint(turnos_bp, url_prefix="/api/turnos")

    @app.errorhandler(ValidationError)
    def datos_invalidos(e):
        detalles = e.errors(include_url=False, include_context=False, include_input=False)
        return jsonify(error="Datos inválidos", detalles=detalles), 400

    @app.errorhandler(429)
    def demasiadas_solicitudes(e):
        return jsonify(error="Demasiados intentos. Probá de nuevo en un rato."), 429

    return app
