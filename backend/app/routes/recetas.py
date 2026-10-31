from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity

from app.repositories.receta_repository import RecetaRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.schemas.receta import PlanSchema, RecetaCrearSchema, RecetaEditarSchema
from app.security.auditoria import registrar_acceso
from app.security.roles import roles_required
from app.services.receta_service import (
    PacienteInvalido,
    PlanNoPermitido,
    RecetaNoEncontrada,
    RecetaService,
    RecetaYaEmitida,
)
from app.utils.serializers import serializar_receta, serializar_receta_para_administrativo

recetas_bp = Blueprint("recetas", __name__)

# strict_slashes=False: /api/recetas y /api/recetas/ funcionan igual. Sin esto, el navegador
# recibe un 308 y bloquea el pedido (CORS no admite redirecciones en el preflight).
SIN_BARRA = {"strict_slashes": False}


def _service() -> RecetaService:
    db = current_app.db
    return RecetaService(RecetaRepository(db), UsuarioRepository(db), current_app.event_bus)


def _responder(accion):
    """Ejecuta una acción del service y traduce sus errores a HTTP."""
    try:
        return accion()
    except RecetaNoEncontrada:
        return jsonify(error="Receta no encontrada"), 404
    except PacienteInvalido:
        return jsonify(error="El paciente indicado no existe"), 400
    except RecetaYaEmitida:
        return jsonify(error="La receta ya fue emitida"), 409
    except PlanNoPermitido:
        return jsonify(error="El plan de medicación solo se registra en recetas, no en órdenes"), 409
    except ValueError as e:
        return jsonify(error=str(e)), 400


@recetas_bp.post("", **SIN_BARRA)
@roles_required("medico")
def crear():
    """Crea una receta o una orden digital en borrador (solo médico)
    ---
    tags: [Recetas]
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            tipo: {type: string, enum: [receta, orden], example: receta}
            paciente_id: {type: string}
            indicaciones: {type: string, example: Tomar después de las comidas}
            medicamentos:
              type: array
              items:
                type: object
                properties:
                  nombre: {type: string, example: Ibuprofeno}
                  dosis: {type: string, example: 400 mg}
                  presentacion: {type: string, example: Comprimidos}
                  horario_toma: {type: string, example: Cada 8 horas}
    responses:
      201:
        description: Receta u orden creada en estado borrador
      400:
        description: Datos inválidos (una receta necesita al menos un medicamento)
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    datos = RecetaCrearSchema.model_validate(request.get_json(silent=True) or {})
    return _responder(lambda: (jsonify(serializar_receta(_service().crear(get_jwt_identity(), datos))), 201))


@recetas_bp.get("", **SIN_BARRA)
@roles_required("medico")
def listar_propias():
    """Recetas y órdenes creadas por el médico autenticado
    ---
    tags: [Recetas]
    responses:
      200:
        description: Lista de recetas del médico, las más nuevas primero
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    recetas = _service().listar_del_medico(get_jwt_identity())
    registrar_acceso("recetas_del_medico")
    return jsonify([serializar_receta(r) for r in recetas])


@recetas_bp.get("/mias")
@roles_required("paciente")
def mis_recetas():
    """Recetas y órdenes que el médico le emitió al paciente autenticado
    ---
    tags: [Recetas]
    responses:
      200:
        description: Solo documentos emitidos (nunca borradores); una receta con plan de medicación aparece cuando el administrativo genera el recordatorio
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    recetas = _service().listar_del_paciente(get_jwt_identity())
    registrar_acceso("recetas_del_paciente")
    return jsonify([serializar_receta(r) for r in recetas])


@recetas_bp.get("/emitidas")
@roles_required("administrativo")
def recetas_emitidas():
    """Recetas y órdenes que emitieron los médicos, con los datos del paciente (solo administrativo)
    ---
    tags: [Recetas]
    responses:
      200:
        description: Documentos emitidos, los más recientes primero. Lleva paciente, médico y si ya se generó el recordatorio, sin medicamentos ni indicaciones
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    recetas = _service().listar_emitidas_con_paciente()
    registrar_acceso("recetas_emitidas")
    return jsonify([serializar_receta_para_administrativo(r) for r in recetas])


@recetas_bp.put("/<receta_id>")
@roles_required("medico")
def editar(receta_id):
    """Edita indicaciones o medicamentos (solo el médico autor, también si ya se emitió)
    ---
    tags: [Recetas]
    parameters:
      - in: path
        name: receta_id
        type: string
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            indicaciones: {type: string}
            medicamentos: {type: array, items: {type: object}}
    responses:
      200:
        description: Receta actualizada
      400:
        description: Datos inválidos
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
      404:
        description: La receta no existe o es de otro médico
    """
    datos = RecetaEditarSchema.model_validate(request.get_json(silent=True) or {})
    return _responder(lambda: jsonify(serializar_receta(_service().editar(receta_id, get_jwt_identity(), datos))))


@recetas_bp.delete("/<receta_id>")
@roles_required("medico")
def eliminar(receta_id):
    """Elimina una receta u orden (solo el médico autor, también si ya se emitió)
    ---
    tags: [Recetas]
    parameters:
      - in: path
        name: receta_id
        type: string
        required: true
    responses:
      200:
        description: Receta eliminada
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
      404:
        description: La receta no existe o es de otro médico
    """

    def accion():
        _service().eliminar(receta_id, get_jwt_identity())
        return jsonify(mensaje="Receta eliminada")

    return _responder(accion)


@recetas_bp.post("/<receta_id>/emitir")
@roles_required("medico")
def emitir(receta_id):
    """Emite la receta u orden al paciente (solo el médico autor)
    ---
    tags: [Recetas]
    parameters:
      - in: path
        name: receta_id
        type: string
        required: true
    responses:
      200:
        description: Receta emitida, ya es visible para el paciente
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
      404:
        description: La receta no existe o es de otro médico
      409:
        description: La receta ya fue emitida
    """
    return _responder(lambda: jsonify(serializar_receta(_service().emitir(receta_id, get_jwt_identity()))))


@recetas_bp.put("/<receta_id>/plan")
@roles_required("medico")
def registrar_plan(receta_id):
    """Registra el plan de medicación de una receta (solo el médico autor)
    ---
    tags: [Recetas]
    parameters:
      - in: path
        name: receta_id
        type: string
        required: true
      - in: body
        name: body
        required: true
        schema:
          type: object
          properties:
            plan:
              type: array
              items:
                type: object
                properties:
                  medicamento: {type: string, example: Ibuprofeno}
                  dosis: {type: string, example: 400 mg}
                  horarios: {type: array, items: {type: string}, example: ["08:00", "16:00", "00:00"]}
                  duracion_dias: {type: integer, example: 7}
    responses:
      200:
        description: Plan registrado
      400:
        description: Datos inválidos
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
      404:
        description: La receta no existe o es de otro médico
      409:
        description: Las órdenes no llevan plan de medicación
    """
    datos = PlanSchema.model_validate(request.get_json(silent=True) or {})
    return _responder(
        lambda: jsonify(serializar_receta(_service().registrar_plan(receta_id, get_jwt_identity(), datos)))
    )
