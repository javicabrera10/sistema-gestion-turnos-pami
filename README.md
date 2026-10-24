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

Patrones: **State** (`patterns/turno_state.py`, estados del turno), **Observer** (`patterns/observer.py` y
`observers.py`, bus de eventos), **Factory** (`patterns/documento_factory.py`, receta u orden).

## Endpoints del Sprint 1

Todos están documentados y se pueden probar en Swagger (`/apidocs`). Salvo login y registro, piden token.

| Método y ruta | Rol | Qué hace |
|---|---|---|
| `POST /api/auth/registro` · `POST /api/auth/login` · `GET /api/auth/me` | todos | Alta de paciente, login y datos propios |
| `GET /api/medicos?especialidad=` | paciente, administrativo | Médicos (id, nombre, especialidad) |
| `POST /api/turnos` | paciente | Solicita un turno (`origen`: `manual` o `voz`) |
| `GET /api/turnos/mios` | paciente | Turnos propios |
| `PATCH /api/turnos/<id>/respuesta` | paciente | `{accion: aceptar \| rechazar}` sobre un turno otorgado |
| `PATCH /api/turnos/<id>/confirmar` · `/rechazar` | paciente | Lo mismo, una ruta por acción |
| `GET /api/turnos?estado=` · `GET /api/turnos/<id>` | administrativo | Solicitudes con datos de contacto del paciente |
| `PATCH /api/turnos/<id>/otorgar` | administrativo | `{medico_id, fecha_hora}`; 409 si el médico ya tiene ese horario |
| `GET /api/notificaciones/mias` · `PATCH /api/notificaciones/<id>/leida` | paciente | Avisos (se crean al otorgar un turno) |
| `GET /api/pacientes?dni=` | médico, administrativo | Busca un paciente (id, nombre, DNI) |
| `POST /api/recetas` | médico | Crea receta (con medicamentos) u orden (con indicaciones), en borrador |
| `GET /api/recetas` | médico | Sus recetas y órdenes |
| `PUT /api/recetas/<id>` · `DELETE /api/recetas/<id>` | médico autor | Edita o elimina, también si ya se emitió |
| `POST /api/recetas/<id>/emitir` | médico autor | Pasa a `emitida`: desde ahí la ve el paciente |
| `PUT /api/recetas/<id>/plan` | médico autor | Plan de medicación: medicamento, dosis, horarios y duración en días |
| `GET /api/recetas/mias` | paciente | Solo lo que el médico ya emitió |

Flujo del turno: `solicitado → otorgado → confirmado | rechazado`.

Los permisos se validan en el servidor con `roles_required`. Si un médico o un paciente intenta usar una ruta de
otro rol recibe 403; si pide un recurso ajeno (receta de otro médico, turno de otro paciente) recibe 404.

## Eventos (Observer)

El `EventBus` se crea una vez en `create_app` (`app.event_bus`). Los services publican y los observers reaccionan.

| Evento | Quién lo publica | Quién reacciona |
|---|---|---|
| `turno.solicitado` | `TurnoService.solicitar` | — |
| `turno.otorgado` | `TurnoAdminService.otorgar` | Crea la notificación al paciente |
| `turno.confirmado` · `turno.rechazado` | `TurnoService` | — |
| `receta.emitida` | `RecetaService.emitir` | — |

Un observer que falla se registra en el log y no corta la operación principal.

## Integrantes

Marcelo Britos, Javier Cabrera
