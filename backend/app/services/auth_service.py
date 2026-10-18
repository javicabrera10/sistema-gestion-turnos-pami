import logging
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from flask_jwt_extended import create_access_token

from app.models.usuario import Paciente
from app.security.passwords import check_password, hash_password

log = logging.getLogger("pami.auth")

MAX_INTENTOS = 5
MINUTOS_BLOQUEO = 15


class CredencialesInvalidas(Exception):
    pass


class CuentaBloqueada(Exception):
    pass


def _ahora() -> datetime:
    # Mongo guarda datetimes en UTC sin zona horaria
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AuthService:
    def __init__(self, usuarios_repo):
        self.repo = usuarios_repo

    def registrar_paciente(self, datos) -> str:
        paciente = Paciente(
            nombre=datos.nombre,
            email=datos.email,
            telefono=datos.telefono,
            dni=datos.dni,
            password_hash=hash_password(datos.password),
        )
        doc = asdict(paciente)
        doc.pop("id")
        id_ = self.repo.crear(doc)
        log.info("registro de paciente id=%s", id_)
        return id_

    def login(self, email: str, password: str):
        usuario = self.repo.buscar_por_email(email)
        if not usuario:
            log.warning("login fallido: email inexistente")
            raise CredencialesInvalidas()

        ahora = _ahora()
        bloqueado = usuario.get("bloqueado_hasta")
        if bloqueado and bloqueado > ahora:
            log.warning("login rechazado: cuenta bloqueada id=%s", usuario["_id"])
            raise CuentaBloqueada()

        if not check_password(password, usuario["password_hash"]):
            intentos = usuario.get("intentos_fallidos", 0) + 1
            if intentos >= MAX_INTENTOS:
                hasta = ahora + timedelta(minutes=MINUTOS_BLOQUEO)
                self.repo.registrar_fallo(usuario["_id"], 0, hasta)
                log.warning("cuenta bloqueada id=%s tras %s intentos", usuario["_id"], MAX_INTENTOS)
            else:
                self.repo.registrar_fallo(usuario["_id"], intentos)
                log.warning("login fallido id=%s intento=%s", usuario["_id"], intentos)
            raise CredencialesInvalidas()

        self.repo.resetear_intentos(usuario["_id"])
        token = create_access_token(
            identity=str(usuario["_id"]),
            additional_claims={"rol": usuario["rol"]},
        )
        log.info("login correcto id=%s rol=%s", usuario["_id"], usuario["rol"])
        return token, usuario
