from flask import Blueprint, current_app, jsonify

from app.security.roles import roles_required
from app.services.recordatorio_service import crear_servicio
from app.services.toma_service import crear_servicio_tomas

recordatorios_bp = Blueprint("recordatorios", __name__)


@recordatorios_bp.post("/ejecutar")
@roles_required("administrativo")
def ejecutar_recordatorios():
    """Crea los recordatorios de turnos y entrega a los pacientes sus recetas con el plan de toma (solo administrativo)
    ---
    tags: [Recordatorios]
    responses:
      200:
        description: Cantidad creada en esta ejecución, enviados son recordatorios de turnos y tomas son recetas con plan entregadas al paciente (0 si no hay nada nuevo)
      401:
        description: Falta el token
      403:
        description: El rol no tiene permiso
    """
    turnos = crear_servicio(current_app.db, current_app.event_bus).procesar()
    tomas = crear_servicio_tomas(current_app.db).procesar()
    return jsonify(enviados=turnos, tomas=tomas)
