from flask import Blueprint, current_app, jsonify

from app.repositories.usuario_repository import UsuarioRepository
from app.security.roles import roles_required
from app.utils.serializers import serializar_usuario

usuarios_bp = Blueprint("usuarios", __name__)


@usuarios_bp.get("")
@roles_required("administrativo")
def listar_usuarios():
    """Lista de usuarios (solo administrativo)
    ---
    tags: [Usuarios]
    responses:
      200:
        description: Lista de usuarios
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    docs = UsuarioRepository(current_app.db).listar()
    return jsonify([serializar_usuario(d) for d in docs])
