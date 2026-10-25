from flask import jsonify
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flasgger import Swagger

jwt = JWTManager()
limiter = Limiter(key_func=get_remote_address)
swagger = Swagger()


@jwt.invalid_token_loader
def _token_invalido(motivo):
    # Token mal formado, con firma falsa o alterado: 401 (la libreria responde 422 por defecto)
    return jsonify(error="Token inválido"), 401