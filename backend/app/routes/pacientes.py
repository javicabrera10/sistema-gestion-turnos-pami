import re

from flask import Blueprint, current_app, jsonify, request

from app.repositories.usuario_repository import UsuarioRepository
from app.security.auditoria import registrar_acceso
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
        example: "30111222"
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
    paciente = UsuarioRepository(current_app.db).buscar_paciente_por_dni(dni)
    registrar_acceso("paciente_por_dni", 0 if paciente is None else 1)
    if paciente is None:
        return jsonify([])
    return jsonify([{"id": str(paciente["_id"]), "nombre": paciente["nombre"], "dni": paciente["dni"]}])
