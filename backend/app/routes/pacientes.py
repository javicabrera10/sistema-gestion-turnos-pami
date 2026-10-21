import re

from flask import Blueprint, current_app, jsonify, request

from app.security.roles import roles_required

pacientes_bp = Blueprint("pacientes", __name__)


@pacientes_bp.get("")
@roles_required("medico", "administrativo")
def buscar_paciente():
    """Busca un paciente por DNI (médico y administrativo)
    ---
    tags: [Pacientes]
    parameters:
      - in: query
        name: dni
        type: string
        required: true
        example: "12345678"
    responses:
      200:
        description: Lista con 0 o 1 paciente (solo id, nombre y DNI)
      400:
        description: DNI inválido
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    dni = request.args.get("dni", "").strip()
    if not re.fullmatch(r"\d{7,8}", dni):
        return jsonify(error="El DNI debe tener 7 u 8 números"), 400
    doc = current_app.db.usuarios.find_one({"rol": "paciente", "dni": dni}, {"nombre": 1, "dni": 1})
    if doc is None:
        return jsonify([])
    return jsonify([{"id": str(doc["_id"]), "nombre": doc["nombre"], "dni": doc["dni"]}])
