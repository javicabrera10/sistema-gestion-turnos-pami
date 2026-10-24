from flask import Blueprint, current_app, jsonify

from app.security.roles import roles_required
from app.services.recordatorio_service import crear_servicio

recordatorios_bp = Blueprint("recordatorios", __name__)


@recordatorios_bp.post("/ejecutar")
@roles_required("administrativo")
def ejecutar_recordatorios():
    """Crea los recordatorios de los turnos confirmados que se acercan (solo administrativo)
    ---
    tags: [Recordatorios]
    responses:
      200:
        description: Cantidad de recordatorios creados en esta ejecución (si no hay nada nuevo, 0)
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    creados = crear_servicio(current_app.db).procesar()
    return jsonify(enviados=creados)
