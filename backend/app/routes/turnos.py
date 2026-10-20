from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.patterns.turno_state import TransicionInvalida
from app.repositories.turno_repository import TurnoRepository
from app.schemas.turno import SolicitudTurnoSchema
from app.security.roles import roles_required
from app.services.turno_service import TurnoNoEncontrado, TurnoService
from app.utils.serializers import serializar_turno

turnos_bp = Blueprint("turnos", __name__)


def _service() -> TurnoService:
    return TurnoService(TurnoRepository(current_app.db))


def _responder(metodo, turno_id: str):
    """Confirma o rechaza un turno y traduce los errores del servicio a HTTP."""
    try:
        turno = metodo(turno_id, get_jwt_identity())
    except TurnoNoEncontrado:
        return jsonify(error="Turno no encontrado"), 404
    except TransicionInvalida as e:
        return jsonify(error=str(e)), 409
    return jsonify(serializar_turno(turno))


@turnos_bp.post("")
@roles_required("paciente")
def solicitar_turno():
    """Solicitud de turno (solo paciente)
    ---
    tags: [Turnos]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            especialidad: {type: string, example: Cardiología}
            fecha_hora: {type: string, example: "2026-11-05T10:30:00"}
            motivo: {type: string, example: Control anual}
    responses:
      201:
        description: Turno creado en estado solicitado
      400:
        description: Datos inválidos
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    datos = SolicitudTurnoSchema.model_validate(request.get_json(silent=True) or {})
    turno = _service().solicitar(get_jwt_identity(), datos)
    return jsonify(serializar_turno(turno)), 201


@turnos_bp.get("/mios")
@roles_required("paciente")
def mis_turnos():
    """Turnos del paciente autenticado
    ---
    tags: [Turnos]
    responses:
      200:
        description: Lista de turnos del paciente, ordenados por fecha
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    turnos = _service().listar_del_paciente(get_jwt_identity())
    return jsonify([serializar_turno(t) for t in turnos])


@turnos_bp.patch("/<turno_id>/confirmar")
@roles_required("paciente")
def confirmar_turno(turno_id):
    """El paciente acepta un turno otorgado
    ---
    tags: [Turnos]
    parameters:
      - in: path
        name: turno_id
        type: string
        required: true
    responses:
      200:
        description: Turno confirmado
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
      404:
        description: El turno no existe o es de otro paciente
      409:
        description: El turno no está en estado otorgado
    """
    return _responder(_service().confirmar, turno_id)


@turnos_bp.patch("/<turno_id>/rechazar")
@roles_required("paciente")
def rechazar_turno(turno_id):
    """El paciente rechaza un turno otorgado
    ---
    tags: [Turnos]
    parameters:
      - in: path
        name: turno_id
        type: string
        required: true
    responses:
      200:
        description: Turno rechazado
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
      404:
        description: El turno no existe o es de otro paciente
      409:
        description: El turno no está en estado otorgado
    """
    return _responder(_service().rechazar, turno_id)
