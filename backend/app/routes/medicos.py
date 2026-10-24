from flask import Blueprint, current_app, jsonify, request

from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.turno import FiltroMedicosSchema
from app.security.roles import roles_required

medicos_bp = Blueprint("medicos", __name__)


@medicos_bp.get("")
@roles_required("paciente", "administrativo")
def listar_medicos():
    """Lista de médicos, opcionalmente por especialidad (paciente y administrativo)
    ---
    tags: [Médicos]
    parameters:
      - in: query
        name: especialidad
        type: string
        required: false
        example: Cardiología
    responses:
      200:
        description: Médicos con id, nombre y especialidad (sin datos de contacto ni credenciales)
      400:
        description: Parámetros inválidos
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    filtro = FiltroMedicosSchema.model_validate(request.args.to_dict())
    medicos = UsuarioRepository(current_app.db).listar_por_rol("medico", filtro.especialidad)
    return jsonify(
        [{"id": str(m["_id"]), "nombre": m["nombre"], "especialidad": m.get("especialidad", "")} for m in medicos]
    )
