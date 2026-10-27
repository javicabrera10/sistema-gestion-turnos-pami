from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.repositories.familiar_repository import FamiliarRepository, MensajeFamiliarRepository
from app.schemas.familiar import FamiliarSchema
from app.security.auditoria import registrar_acceso
from app.security.roles import roles_required
from app.services.familiar_service import FamiliarService
from app.utils.serializers import serializar_familiar, serializar_mensaje_familiar

familiar_bp = Blueprint("familiar", __name__)

# strict_slashes=False: /api/familiar y /api/familiar/ funcionan igual (ver recetas.py)
SIN_BARRA = {"strict_slashes": False}


def _service() -> FamiliarService:
    db = current_app.db
    return FamiliarService(FamiliarRepository(db), MensajeFamiliarRepository(db))


def _responder(familiar):
    return jsonify(familiar=None if familiar is None else serializar_familiar(familiar))


@familiar_bp.get("", **SIN_BARRA)
@roles_required("paciente")
def mi_familiar():
    """Familiar autorizado del paciente autenticado (solo paciente)
    ---
    tags: [Familiar autorizado]
    responses:
      200:
        description: El familiar autorizado, o familiar null si todavía no autorizó a nadie
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    familiar = _service().obtener(get_jwt_identity())
    registrar_acceso("familiar_autorizado")
    return _responder(familiar)


@familiar_bp.put("", **SIN_BARRA)
@roles_required("paciente")
def autorizar_familiar():
    """Autoriza a un familiar para recibir avisos de los turnos, o cambia sus datos (solo paciente)
    ---
    tags: [Familiar autorizado]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [nombre, parentesco, canal, contacto, consentimiento]
          properties:
            nombre: {type: string, example: "Marta Gómez"}
            parentesco: {type: string, example: "Hija"}
            canal: {type: string, enum: [sms, email]}
            contacto: {type: string, example: "+5492615551234"}
            consentimiento: {type: boolean, example: true}
    responses:
      200:
        description: Familiar autorizado
      400:
        description: Datos inválidos, o falta el consentimiento
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    datos = FamiliarSchema.model_validate(request.get_json(silent=True) or {})
    return _responder(_service().guardar(get_jwt_identity(), datos))


@familiar_bp.delete("", **SIN_BARRA)
@roles_required("paciente")
def quitar_autorizacion():
    """Quita la autorización: desde ese momento no se le avisa más al familiar (solo paciente)
    ---
    tags: [Familiar autorizado]
    responses:
      200:
        description: Autorización quitada (familiar null). Si no había nadie autorizado responde igual
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    _service().revocar(get_jwt_identity())
    return _responder(None)


@familiar_bp.get("/avisos")
@roles_required("paciente")
def avisos_enviados():
    """Avisos que se le enviaron al familiar del paciente, los más nuevos primero (solo paciente)
    ---
    tags: [Familiar autorizado]
    responses:
      200:
        description: Lista de avisos con canal, destino, texto y fecha
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    avisos = _service().listar_avisos(get_jwt_identity())
    registrar_acceso("avisos_del_familiar", resultados=len(avisos))
    return jsonify([serializar_mensaje_familiar(a) for a in avisos])
