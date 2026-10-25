from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import limiter
from app.repositories.usuario_repository import EmailDuplicadoError, UsuarioRepository
from app.schemas.auth import LoginSchema, RegistroPacienteSchema
from app.services.auth_service import AuthService, CredencialesInvalidas, CuentaBloqueada
from app.utils.serializers import serializar_usuario

auth_bp = Blueprint("auth", __name__)


def _service() -> AuthService:
    return AuthService(UsuarioRepository(current_app.db))


@auth_bp.post("/registro")
@limiter.limit("10 per minute")
def registro():
    """Registro de un paciente
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            nombre: {type: string}
            email: {type: string}
            telefono: {type: string}
            dni: {type: string}
            password: {type: string}
    responses:
      201:
        description: Paciente creado
      400:
        description: Datos inválidos
      409:
        description: El email ya está registrado
      429:
        description: Demasiados intentos
    """
    datos = RegistroPacienteSchema.model_validate(request.get_json(silent=True) or {})
    try:
        id_ = _service().registrar_paciente(datos)
    except EmailDuplicadoError:
        return jsonify(error="El email ya está registrado"), 409
    return jsonify(id=id_), 201


@auth_bp.post("/login")
@limiter.limit("10 per minute")
def login():
    """Inicio de sesión
    ---
    tags: [Auth]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            email: {type: string}
            password: {type: string}
    responses:
      200:
        description: Devuelve el token JWT y el rol
      401:
        description: Credenciales inválidas
      423:
        description: Cuenta bloqueada temporalmente
      429:
        description: Demasiados intentos
    """
    datos = LoginSchema.model_validate(request.get_json(silent=True) or {})
    try:
        token, usuario = _service().login(datos.email, datos.password)
    except CuentaBloqueada:
        return jsonify(error="Cuenta bloqueada temporalmente por intentos fallidos"), 423
    except CredencialesInvalidas:
        return jsonify(error="Email o contraseña incorrectos"), 401
    return jsonify(access_token=token, rol=usuario["rol"], nombre=usuario["nombre"])


@auth_bp.get("/me")
@jwt_required()
def me():
    """Datos del usuario autenticado
    ---
    tags: [Auth]
    responses:
      200:
        description: Datos del usuario
      401:
        description: Falta el token o es inválido
    """
    usuario = UsuarioRepository(current_app.db).get_by_id(get_jwt_identity())
    return jsonify(serializar_usuario(usuario))
