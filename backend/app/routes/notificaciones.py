from flask import Blueprint, current_app, jsonify
from flask_jwt_extended import get_jwt_identity

from app.repositories.notificacion_repository import NotificacionRepository
from app.security.roles import roles_required
from app.services.notificacion_service import NotificacionNoEncontrada, NotificacionService
from app.utils.serializers import serializar_notificacion

notificaciones_bp = Blueprint("notificaciones", __name__)


def _service() -> NotificacionService:
    return NotificacionService(NotificacionRepository(current_app.db))


@notificaciones_bp.get("/mias")
@roles_required("paciente", "administrativo")
def mis_notificaciones():
    """Notificaciones del usuario autenticado: paciente o administrativo (las más nuevas primero)
    ---
    tags: [Notificaciones]
    responses:
      200:
        description: Lista de notificaciones con mensaje, fecha y si fue leída
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    notifs = _service().listar_mias(get_jwt_identity())
    return jsonify([serializar_notificacion(n) for n in notifs])


@notificaciones_bp.patch("/<notificacion_id>/leida")
@roles_required("paciente", "administrativo")
def marcar_leida(notificacion_id):
    """Marca una notificación como leída (solo su destinatario: paciente o administrativo)
    ---
    tags: [Notificaciones]
    parameters:
      - in: path
        name: notificacion_id
        type: string
        required: true
    responses:
      200:
        description: Notificación marcada como leída
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
      404:
        description: La notificación no existe o es de otra persona
    """
    try:
        notif = _service().marcar_leida(notificacion_id, get_jwt_identity())
    except NotificacionNoEncontrada:
        return jsonify(error="Notificación no encontrada"), 404
    return jsonify(serializar_notificacion(notif))
