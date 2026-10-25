from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.preferencias import PreferenciasSchema
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


@usuarios_bp.get("/me/preferencias")
@jwt_required()
def ver_preferencias():
    """Preferencias de accesibilidad del usuario logueado
    ---
    tags: [Usuarios]
    responses:
      200:
        description: tamano_letra (normal, grande o muy_grande), alto_contraste y voz_activada
      401:
        description: Falta el token o venció
      404:
        description: El usuario ya no existe
    """
    prefs = UsuarioRepository(current_app.db).obtener_preferencias(get_jwt_identity())
    if prefs is None:
        return jsonify(error="Usuario no encontrado"), 404
    return jsonify(prefs)


@usuarios_bp.put("/me/preferencias")
@jwt_required()
def guardar_preferencias():
    """Guarda las preferencias de accesibilidad del usuario logueado (siempre las propias)
    ---
    tags: [Usuarios]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [tamano_letra, alto_contraste, voz_activada]
          properties:
            tamano_letra:
              type: string
              enum: [normal, grande, muy_grande]
            alto_contraste:
              type: boolean
            voz_activada:
              type: boolean
    responses:
      200:
        description: Preferencias guardadas
      400:
        description: Datos inválidos
      401:
        description: Falta el token o venció
      404:
        description: El usuario ya no existe
    """
    datos = PreferenciasSchema.model_validate(request.get_json(silent=True))
    repo = UsuarioRepository(current_app.db)
    usuario_id = get_jwt_identity()
    if repo.obtener_preferencias(usuario_id) is None:
        return jsonify(error="Usuario no encontrado"), 404
    prefs = datos.model_dump()
    repo.guardar_preferencias(usuario_id, prefs)
    return jsonify(prefs)