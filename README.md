# App PAMI – Gestión de turnos y notificaciones

TP Integrador de Programación II (IES 9-023 CESIT). Stack: Flask, MongoDB, React.

## Backend

1. Levantar MongoDB:
   `docker run -d -p 27017:27017 --name mongo-pami -v mongo-pami-data:/data/db mongo:4`
2. Configurar el entorno:
   ```
   cd backend
   Copy-Item .env.example .env
   uv sync
   ```
   Completar `SECRET_KEY` y `JWT_SECRET_KEY` en el `.env` con valores largos y aleatorios.
3. Crear índices y usuarios demo: `uv run python -m scripts.init_db`
4. Ejecutar: `uv run python run.py`
5. Documentación Swagger: http://127.0.0.1:5000/apidocs
6. Tests: `uv run pytest -v`

## Usuarios demo (datos ficticios)

| Rol | Email | Contraseña |
|---|---|---|
| administrativo | admin@pamiapp.com | Admin1234 |
| médico | medico@pamiapp.com | Medico1234 |
| paciente | paciente@pamiapp.com | Paciente1234 |

## Estructura del backend

`routes` (endpoints) → `services` (lógica de negocio) → `repositories` (acceso a MongoDB).

## Integrantes

Marcelo Britos, Javier Cabrera
