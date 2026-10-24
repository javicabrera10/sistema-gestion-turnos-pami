from flask import Flask, jsonify
from flask_cors import CORS
from pydantic import ValidationError
from pymongo import MongoClient

from .config import Config
from .extensions import jwt, limiter, swagger
from .patterns.observer import EventBus


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
    # Observer: se crea una sola vez; los services publican eventos y los observers reaccionan
    app.event_bus = EventBus()

    from .routes.auth import auth_bp
    from .routes.health import health_bp
    from .routes.usuarios import usuarios_bp
    from .routes.turnos import turnos_bp
    from .routes.turnos_admin import turnos_admin_bp
    from .patterns.observers import registrar_observers
    from .routes.medicos import medicos_bp
    from .routes.notificaciones import notificaciones_bp
    from .routes.pacientes import pacientes_bp
    from .routes.recetas import recetas_bp
    from .routes.recordatorios import recordatorios_bp

    app.register_blueprint(health_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(usuarios_bp, url_prefix="/api/usuarios")
    app.register_blueprint(turnos_bp, url_prefix="/api/turnos")
    app.register_blueprint(turnos_admin_bp, url_prefix="/api/turnos")
    app.register_blueprint(recetas_bp, url_prefix="/api/recetas")
    app.register_blueprint(medicos_bp, url_prefix="/api/medicos")
    app.register_blueprint(pacientes_bp, url_prefix="/api/pacientes")
    app.register_blueprint(notificaciones_bp, url_prefix="/api/notificaciones")
    app.register_blueprint(recordatorios_bp, url_prefix="/api/recordatorios")
    registrar_observers(app)

    @app.errorhandler(ValidationError)
    def datos_invalidos(e):
        detalles = e.errors(include_url=False, include_context=False, include_input=False)
        return jsonify(error="Datos inválidos", detalles=detalles), 400

    @app.errorhandler(429)
    def demasiadas_solicitudes(e):
        return jsonify(error="Demasiados intentos. Probá de nuevo en un rato."), 429

    return app