# App PAMI – Gestión de turnos y notificaciones

Trabajo Práctico Integrador de **Programación II** – IES 9-023 CESIT
Tecnicatura Superior en Desarrollo de Software

## Integrantes

- Javier Cabrera
- Marcelo Britos

## Introducción

**App PAMI** es una aplicación web para gestionar turnos médicos, recetas y recordatorios de medicación de afiliados de PAMI. Pensada para adultos mayores, incluye opciones de accesibilidad y un modo de uso por voz.

Participan tres roles, cada uno con su propia pantalla:

| Rol | Qué puede hacer |
|---|---|
| **Paciente** | Solicitar turnos (de forma manual o por voz), aceptar o rechazar el turno que le otorgan, ver sus recetas y su plan de medicación, leer sus notificaciones, configurar un familiar autorizado y ajustar la accesibilidad de la interfaz. |
| **Administrativo** | Revisar las solicitudes de turno, otorgar turnos asignando médico y horario (el sistema evita que un médico tenga dos turnos a la misma hora), ver las recetas emitidas y generar los recordatorios. |
| **Médico** | Crear, editar y emitir recetas y órdenes, y definir el plan de medicación (medicamento, dosis, horarios y duración). |

**Flujo del turno:** `solicitado → otorgado → confirmado | rechazado`.

**Funcionalidades principales**

- Autenticación con JWT y permisos por rol.
- Notificaciones al paciente cuando se le otorga un turno.
- Recordatorios automáticos de turnos confirmados (24 horas y 2 horas antes).
- Avisos a un familiar autorizado por SMS o email, según el canal que elija el paciente.
- Interacción por voz y preferencias de accesibilidad.
- Documentación interactiva de la API con Swagger.

## Tecnologías

- **Backend:** Python 3.12, Flask, Pydantic, Flask-JWT-Extended, Flask-Limiter, bcrypt, Flasgger (Swagger).
- **Base de datos:** MongoDB (PyMongo).
- **Frontend:** React 19, Vite, React Router.
- **Pruebas:** pytest y mongomock (backend), Vitest y Testing Library (frontend).
- **Gestor de paquetes del backend:** [uv](https://docs.astral.sh/uv/).

## Arquitectura

El backend sigue una arquitectura en capas:

`routes` (endpoints) → `services` (lógica de negocio) → `repositories` (acceso a MongoDB)

**Patrones de diseño aplicados**

| Patrón | Dónde | Para qué |
|---|---|---|
| Repository | `app/repositories/` | Aísla el acceso a la base de datos. |
| Observer | `patterns/observer.py`, `observers.py` | Bus de eventos: los servicios publican y los observers reaccionan. |
| State | `patterns/turno_state.py` | Estados y transiciones del turno. |
| Factory | `patterns/documento_factory.py` | Crea una receta o una orden según el caso. |
| Strategy | `patterns/canal_strategy.py`, `recordatorio_strategy.py` | Canal de aviso (SMS o email) y reglas de recordatorio. |

El detalle de cada patrón está en [`docs/PATRONES.md`](docs/PATRONES.md).

## Estructura del proyecto

```
APP_PAMI/
├── backend/             API en Flask
│   ├── app/
│   │   ├── routes/          endpoints
│   │   ├── services/        lógica de negocio
│   │   ├── repositories/    acceso a MongoDB
│   │   ├── patterns/        State, Observer, Factory, Strategy
│   │   ├── schemas/         validación con Pydantic
│   │   ├── models/
│   │   ├── security/        roles, contraseñas, auditoría, encabezados
│   │   └── utils/
│   ├── scripts/         init_db.py y enviar_recordatorios.py
│   ├── tests/           pruebas unitarias y e2e
│   ├── run.py
│   ├── pyproject.toml
│   └── .env.example
├── frontend/            app en React + Vite
│   └── src/             pages, components, context, hooks, services, utils
└── docs/                PATRONES.md, SEGURIDAD.md, WIRESHARK.md
```

## Requisitos previos

- [Python 3.12 o superior](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Node.js](https://nodejs.org/) (con npm)
- [Docker](https://www.docker.com/) para levantar MongoDB (o una instalación local de MongoDB)

## Cómo ejecutar el proyecto

### 1. Levantar MongoDB

```bash
docker run -d -p 27017:27017 --name mongo-pami -v mongo-pami-data:/data/db mongo:4
```

Si el contenedor ya existe, alcanza con `docker start mongo-pami`.

### 2. Configurar y ejecutar el backend

```bash
cd backend
```

Crear el archivo `.env` a partir del ejemplo:

```powershell
# Windows (PowerShell)
Copy-Item .env.example .env
```

```bash
# Linux / macOS
cp .env.example .env
```

Completar el `.env`. **Todas las variables deben tener valor**, porque una variable vacía pisa el valor por defecto:

```env
SECRET_KEY=<un valor largo y aleatorio>
JWT_SECRET_KEY=<otro valor largo y aleatorio>
MONGO_URI=mongodb://127.0.0.1:27017
MONGO_DB=pami_db
CORS_ORIGINS=http://localhost:5173
```

Si faltan `SECRET_KEY` o `JWT_SECRET_KEY`, la aplicación no arranca. Se puede generar una clave con:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Instalar las dependencias, crear la base y levantar el servidor:

```bash
uv sync
uv run python -m scripts.init_db
uv run python run.py
```

La API queda disponible en http://127.0.0.1:5000 y la documentación Swagger en http://127.0.0.1:5000/apidocs.

### 3. Ejecutar el frontend

En otra terminal:

```bash
cd frontend
npm install
npm run dev
```

La aplicación queda disponible en http://localhost:5173.

Por defecto el frontend consulta a `http://127.0.0.1:5000/api`. Si el backend corre en otra dirección, se puede definir la variable `VITE_API_URL` en un archivo `frontend/.env`.

## Scripts del backend

Se ejecutan desde la carpeta `backend/`.

| Script | Comando | Qué hace |
|---|---|---|
| `init_db` | `uv run python -m scripts.init_db` | Crea los índices de MongoDB y los usuarios demo. Se puede correr más de una vez: no duplica usuarios. |
| `enviar_recordatorios` | `uv run python -m scripts.enviar_recordatorios` | Crea los recordatorios de los turnos confirmados que se acercan (24 h y 2 h antes). Cada recordatorio se crea una sola vez, así que se puede ejecutar las veces que se quiera. |

Para automatizar `enviar_recordatorios` se puede programar, por ejemplo, cada 15 minutos con cron (Linux) o con el Programador de tareas (Windows).

El recordatorio de medicación de las recetas no lo genera este script: lo genera el administrativo con el botón **Generar recordatorios** de su panel.

## Usuarios demo

Datos ficticios, creados por `init_db`:

| Rol | Email | Contraseña |
|---|---|---|
| Administrativo | admin@pamiapp.com | Admin1234 |
| Médico | medico@pamiapp.com | Medico1234 |
| Paciente | paciente@pamiapp.com | Paciente1234 |

## Pruebas

```bash
# Backend (desde backend/)
uv run pytest -v

# Frontend (desde frontend/)
npm test
```

## Endpoints principales

Están documentados y se pueden probar en Swagger (`/apidocs`). Salvo login y registro, todos piden token.

| Método y ruta | Rol | Qué hace |
|---|---|---|
| `POST /api/auth/registro` · `POST /api/auth/login` · `GET /api/auth/me` | todos | Alta de paciente, login y datos propios. |
| `GET /api/medicos` | paciente, administrativo | Lista de médicos, con filtro por especialidad. |
| `POST /api/turnos` | paciente | Solicita un turno (`origen`: `manual` o `voz`). |
| `GET /api/turnos/mios` | paciente | Turnos propios. |
| `PATCH /api/turnos/<id>/respuesta` | paciente | Acepta o rechaza un turno otorgado. |
| `GET /api/turnos` · `PATCH /api/turnos/<id>/otorgar` | administrativo | Lista solicitudes y otorga turnos (409 si el médico ya tiene ese horario). |
| `GET /api/notificaciones/mias` | paciente | Notificaciones propias. |
| `GET /api/pacientes?dni=` | médico, administrativo | Busca un paciente por DNI. |
| `POST /api/recetas` · `PUT` · `DELETE` · `POST /<id>/emitir` · `PUT /<id>/plan` | médico | Gestiona recetas, órdenes y plan de medicación. |
| `GET /api/recetas/mias` | paciente | Recetas emitidas para el paciente. |
| `GET /api/recetas/emitidas` | administrativo | Recetas y órdenes emitidas. |
| `POST /api/recordatorios/ejecutar` | administrativo | Genera los recordatorios. |
| `GET/PUT/DELETE /api/familiar` · `GET /api/familiar/avisos` | paciente | Familiar autorizado y sus avisos. |

Los permisos se validan siempre en el servidor. Un rol sin permiso recibe 403, y un recurso ajeno responde 404.

## Seguridad

- Contraseñas con hash bcrypt y política de contraseña segura.
- Tokens JWT firmados, con vencimiento a los 30 minutos.
- Límite de pedidos por IP y bloqueo temporal de la cuenta tras 5 intentos fallidos.
- Validación estricta de entradas con Pydantic (protección contra inyección NoSQL).
- Control de acceso por rol y por propietario del recurso.
- Encabezados de seguridad, registro de accesos a datos sensibles y secretos por variables de entorno.
- Análisis comparativo de tráfico HTTP vs. HTTPS con Wireshark.

Documentación técnica: [`docs/SEGURIDAD.md`](docs/SEGURIDAD.md) y [`docs/WIRESHARK.md`](docs/WIRESHARK.md).

> **Nota:** `run.py` inicia Flask con `debug=True`, algo válido solo para desarrollo.
