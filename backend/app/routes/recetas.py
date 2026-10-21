from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from app.security.roles import roles_required
from app.repositories.receta_repository import RecetaRepository
from app.services.receta_service import RecetaService

recetas_bp = Blueprint("recetas", __name__)

def _service():
    return RecetaService(RecetaRepository(current_app.db))

@recetas_bp.post("/")
@jwt_required()
@roles_required("medico")
def crear():
    """Crear receta
    ---
    tags: [Recetas]
    responses:
      201:
        description: Receta creada
    """
    datos = request.get_json()
    medico_id = get_jwt_identity()
    id_ = _service().crear_receta(datos["paciente_id"], medico_id, datos["medicamentos"])
    return jsonify(id=id_), 201

@recetas_bp.post("/<id>/emitir")
@jwt_required()
@roles_required("medico")
def emitir(id):
    """Emitir receta al paciente
    ---
    tags: [Recetas]
    """
    try:
        _service().emitir_receta(id, get_jwt_identity())
        return jsonify(msg="Receta emitida")
    except ValueError as e:
        return jsonify(error=str(e)), 403
