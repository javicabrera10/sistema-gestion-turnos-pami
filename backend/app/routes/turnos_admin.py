from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.patterns.turno_state import TransicionInvalida
from app.repositories.turno_repository import TurnoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.turno import FiltroTurnosSchema, OtorgarTurnoSchema, ReprogramarTurnoSchema
from app.security.roles import roles_required
from app.services.turno_admin_service import HorarioOcupado, MedicoInvalido, TurnoAdminService
from app.services.turno_service import TurnoNoEncontrado
from app.utils.serializers import serializar_turno_con_paciente

# Mismo prefijo (/api/turnos) que turnos_bp: acá van las rutas del administrativo
turnos_admin_bp = Blueprint("turnos_admin", __name__)


def _service() -> TurnoAdminService:
    return TurnoAdminService(
        TurnoRepository(current_app.db), UsuarioRepository(current_app.db), current_app.event_bus
    )


@turnos_admin_bp.get("")
@roles_required("administrativo")
def listar_turnos():
    """Lista de turnos con los datos del paciente (solo administrativo)
    ---
    tags: [Turnos]
    parameters:
      - in: query
        name: estado
        type: string
        required: false
        enum: [solicitado, otorgado, confirmado, rechazado, reprogramado, cancelado]
    responses:
      200:
        description: Turnos ordenados por fecha
      400:
        description: Estado inválido
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    filtro = FiltroTurnosSchema.model_validate(request.args.to_dict())
    turnos = _service().listar(filtro.estado)
    return jsonify([serializar_turno_con_paciente(t) for t in turnos])


@turnos_admin_bp.get("/<turno_id>")
@roles_required("administrativo")
def ver_turno(turno_id):
    """Detalle de un turno con los datos del paciente (solo administrativo)
    ---
    tags: [Turnos]
    parameters:
      - in: path
        name: turno_id
        type: string
        required: true
    responses:
      200:
        description: Datos del turno y del paciente
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
      404:
        description: El turno no existe
    """
    try:
        turno = _service().obtener(turno_id)
    except TurnoNoEncontrado:
        return jsonify(error="Turno no encontrado"), 404
    return jsonify(serializar_turno_con_paciente(turno))


@turnos_admin_bp.patch("/<turno_id>/otorgar")
@roles_required("administrativo")
def otorgar_turno(turno_id):
    """Otorga un turno solicitado: asigna médico, fecha y hora (solo administrativo)
    ---
    tags: [Turnos]
    parameters:
      - in: path
        name: turno_id
        type: string
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            medico_id: {type: string}
            fecha_hora: {type: string, example: "2026-11-05T10:30:00"}
    responses:
      200:
        description: Turno otorgado, queda visible para el paciente
      400:
        description: Datos inválidos o médico inexistente
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
      404:
        description: El turno no existe
      409:
        description: El turno no está en estado solicitado, o el médico ya tiene un turno a esa hora
    """
    datos = OtorgarTurnoSchema.model_validate(request.get_json(silent=True) or {})
    try:
        turno = _service().otorgar(turno_id, get_jwt_identity(), datos)
    except TurnoNoEncontrado:
        return jsonify(error="Turno no encontrado"), 404
    except MedicoInvalido:
        return jsonify(error="El médico indicado no existe"), 400
    except TransicionInvalida as e:
        return jsonify(error=str(e)), 409
    except HorarioOcupado:
        return jsonify(error="El médico ya tiene un turno a esa fecha y hora"), 409
    return jsonify(serializar_turno_con_paciente(turno))


@turnos_admin_bp.patch("/<turno_id>/reprogramar")
@roles_required("administrativo")
def reprogramar_turno(turno_id):
    """Cambia la fecha y hora de un turno; el paciente recibe un aviso y tiene que responder (solo administrativo)
    ---
    tags: [Turnos]
    parameters:
      - in: path
        name: turno_id
        type: string
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            fecha_hora: {type: string, example: "2026-11-12T09:00:00"}
    responses:
      200:
        description: Turno reprogramado, queda en estado reprogramado
      400:
        description: Fecha inválida o en el pasado
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
      404:
        description: El turno no existe
      409:
        description: El turno no se puede reprogramar en su estado actual, o el médico ya tiene un turno a esa hora
    """
    datos = ReprogramarTurnoSchema.model_validate(request.get_json(silent=True) or {})
    try:
        turno = _service().reprogramar(turno_id, get_jwt_identity(), datos)
    except TurnoNoEncontrado:
        return jsonify(error="Turno no encontrado"), 404
    except TransicionInvalida as e:
        return jsonify(error=str(e)), 409
    except HorarioOcupado:
        return jsonify(error="El médico ya tiene un turno a esa fecha y hora"), 409
    return jsonify(serializar_turno_con_paciente(turno))


@turnos_admin_bp.patch("/<turno_id>/cancelar")
@roles_required("administrativo")
def cancelar_turno(turno_id):
    """Cancela un turno otorgado, confirmado o reprogramado; el paciente recibe un aviso (solo administrativo)
    ---
    tags: [Turnos]
    parameters:
      - in: path
        name: turno_id
        type: string
        required: true
    responses:
      200:
        description: Turno cancelado
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
      404:
        description: El turno no existe
      409:
        description: El turno no se puede cancelar en su estado actual
    """
    try:
        turno = _service().cancelar(turno_id, get_jwt_identity())
    except TurnoNoEncontrado:
        return jsonify(error="Turno no encontrado"), 404
    except TransicionInvalida as e:
        return jsonify(error=str(e)), 409
    return jsonify(serializar_turno_con_paciente(turno))
