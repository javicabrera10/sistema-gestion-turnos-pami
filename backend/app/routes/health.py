from flask import Blueprint, current_app, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    """Estado del servicio
    ---
    tags: [Sistema]
    responses:
      200:
        description: El servicio está funcionando
    """
    return jsonify(status="ok")


@health_bp.get("/health/db")
def health_db():
    """Estado de la conexión a MongoDB
    ---
    tags: [Sistema]
    responses:
      200:
        description: Conexión a MongoDB correcta
      503:
        description: No se pudo conectar a MongoDB
    """
    try:
        current_app.db.command("ping")
        return jsonify(status="ok", db=current_app.config["MONGO_DB"])
    except Exception:
        return jsonify(status="error", detail="No se pudo conectar a MongoDB"), 503