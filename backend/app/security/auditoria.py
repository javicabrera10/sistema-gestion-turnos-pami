"""Registro de accesos a datos de pacientes y recetas (solo lecturas)."""
import logging

from flask_jwt_extended import get_jwt, get_jwt_identity

log = logging.getLogger("pami.acceso")


def registrar_acceso(recurso, resultados=None):
    """Deja en el log quién (id y rol) consultó un recurso.

    Se llama dentro de una ruta ya protegida con roles_required. No guarda contenido clínico,
    DNI, contraseñas ni tokens: solo quién consultó qué tipo de dato.
    """
    extra = "" if resultados is None else f" resultados={resultados}"
    log.info("lectura de %s usuario_id=%s rol=%s%s", recurso, get_jwt_identity(), get_jwt().get("rol"), extra)