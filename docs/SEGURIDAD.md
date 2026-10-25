# Seguridad de la aplicación PAMI

Sistema de gestión de turnos y notificaciones. Trabajo Práctico Integrador de Programación II, Sprint 2.
Este documento describe cada mecanismo de seguridad del backend, en qué archivo está, qué ataque evita y cómo se prueba.

## 1. Resumen

| Amenaza | Mecanismo | Dónde está |
|---|---|---|
| Fuerza bruta | Límite de pedidos por IP y bloqueo temporal de la cuenta | `routes/auth.py`, `extensions.py`, `services/auth_service.py` |
| Inyección NoSQL | Validación estricta de los datos de entrada con Pydantic | `schemas/`, `routes/` |
| Contraseñas débiles o robadas | Hash con bcrypt y política de contraseña | `security/passwords.py`, `schemas/auth.py` |
| Robo o falsificación de sesión | Token JWT firmado, de corta duración | `config.py`, `extensions.py`, `services/auth_service.py` |
| Acceso a datos ajenos | Permisos por rol y por propietario | `security/roles.py`, `services/` |
| Fuga de datos sensibles | Datos mínimos, registro de accesos y encabezados | `utils/serializers.py`, `security/auditoria.py`, `security/headers.py` |
| Configuración insegura | Secretos y CORS por variable de entorno | `config.py`, `.env.example` |

Todas las rutas indicadas están dentro de `backend/app/`. La última verificación de las pruebas fue de 426 pruebas pasando.

## 2. Fuerza bruta

**Qué hace.**
- El inicio de sesión y el registro aceptan como máximo 10 pedidos por minuto desde la misma IP. Pasado ese límite responden 429.
- Tras 5 contraseñas incorrectas seguidas, la cuenta se bloquea 15 minutos. Durante el bloqueo se responde 423, incluso con la contraseña correcta. Un inicio de sesión correcto reinicia el contador.
- El mensaje de error es el mismo si el email no existe o la contraseña es incorrecta ("Email o contraseña incorrectos"), para no revelar qué cuentas existen.

**Dónde.** `routes/auth.py` (`@limiter.limit("10 per minute")`), `extensions.py` (el limitador, por IP), `services/auth_service.py` (`MAX_INTENTOS = 5`, `MINUTOS_BLOQUEO = 15`) y `__init__.py` (respuesta 429).

**Ataque que evita.** Probar muchas contraseñas contra una cuenta, o muchas cuentas desde un mismo origen, hasta acertar.

**Cómo se prueba.** `tests/e2e/test_auth.py` (`test_rate_limit_en_login`, `test_bloqueo_tras_cinco_intentos_fallidos`) y `tests/e2e/test_seguridad.py` (`test_rate_limit_en_registro`).

## 3. Inyección NoSQL

**Qué hace.** Todo cuerpo JSON se valida con un esquema de Pydantic antes de llegar a la base:
- Cada campo tiene un tipo fijo (texto, email, número, lista de valores permitidos). Un objeto como `{"$ne": ""}` en lugar de un texto se rechaza con 400, así que ningún operador de MongoDB llega a una consulta.
- Los esquemas usan `extra="forbid"`: no se aceptan campos que no estén definidos. Por eso nadie puede elegir su propio rol al registrarse, ni mandar un `estado` o un `paciente_id` ajeno al pedir un turno.
- El DNI que se busca por URL se valida con una expresión regular (7 u 8 dígitos) antes de consultar.
- La respuesta de error de validación no devuelve los datos que se enviaron.

**Dónde.** `schemas/` (`auth.py`, `turno.py`, `receta.py`, `preferencias.py`), `routes/pacientes.py` y el manejador de `ValidationError` en `__init__.py`.

**Ataque que evita.** Inyección de operadores de MongoDB (por ejemplo, entrar sin conocer la contraseña con `{"$ne": ""}`) y asignación masiva de campos.

**Cómo se prueba.** `tests/unit/test_schemas.py` (`test_login_rechaza_inyeccion_nosql`, `test_registro_rechaza_campo_rol`) y `tests/e2e/test_turnos.py` (`test_solicitar_datos_invalidos`).

## 4. Contraseñas

**Qué hace.**
- Se guarda solo el hash, con bcrypt y una sal aleatoria distinta por contraseña. El costo es de 12 rondas, configurable con la variable `BCRYPT_ROUNDS` (en las pruebas se baja para que corran rápido).
- Al registrarse se exige una contraseña de al menos 8 caracteres, con mayúscula, minúscula y número. Bcrypt solo usa los primeros 72 bytes, así que una contraseña más larga se rechaza en lugar de truncarse en silencio.
- El hash nunca sale de la API: los listados lo excluyen y el serializador lo oculta.
- El inicio de sesión no exige complejidad, solo que haya una contraseña. Así los usuarios existentes y los de demostración siguen pudiendo entrar.

**Dónde.** `security/passwords.py` (`hash_password`, `check_password`), `schemas/auth.py` (`_contrasena_segura`, `_max_72_bytes`), `utils/serializers.py` y `repositories/usuario_repository.py`.

**Ataque que evita.** Que una filtración de la base exponga las contraseñas, los ataques con tablas precalculadas (la sal) y las contraseñas triviales.

**Cómo se prueba.** `tests/unit/test_passwords.py`, `tests/e2e/test_seguridad.py` (`test_registro_exige_contrasena_segura`) y `tests/e2e/test_auth.py` (`test_rol_permitido_y_denegado` verifica que `password_hash` no aparece en las respuestas).

## 5. Tokens y sesión

**Qué hace.**
- Al iniciar sesión se emite un token JWT firmado (HS256) con el identificador del usuario y su rol. Vence a los 30 minutos.
- La clave de firma viene de una variable de entorno, nunca del código.
- Un token vencido, mal formado, firmado con otra clave o con el rol modificado se rechaza con 401. Modificar el rol dentro del token invalida la firma.

**Dónde.** `config.py` (`JWT_ACCESS_TOKEN_EXPIRES`, `JWT_SECRET_KEY`), `services/auth_service.py` (emisión) y `extensions.py` (respuesta 401 ante un token inválido, ya que la librería responde 422 por defecto).

**Ataque que evita.** Falsificar una sesión, reutilizar un token viejo o subir de rol alterando el contenido del token.

**Cómo se prueba.** `tests/e2e/test_seguridad.py`: `test_token_vencido_da_401`, `test_token_firmado_con_otra_clave_da_401`, `test_token_con_el_rol_alterado_da_401` y `test_token_mal_formado_da_401`.

## 6. Control de acceso por rol y por propietario

**Qué hace.**
- Cada ruta declara qué roles pueden usarla con el decorador `roles_required`. Sin token responde 401, y con un rol no permitido responde 403. Los permisos se validan siempre en el backend, nunca solo en la interfaz.
- Además del rol, se controla que el recurso pertenezca a quien lo pide: un paciente solo ve y responde sus turnos, un médico solo edita sus recetas, y las preferencias de accesibilidad se leen y guardan siempre sobre la cuenta del token, nunca sobre un identificador enviado por el cliente. Si el recurso es de otra persona, la respuesta es 404, igual que si no existiera.

**Dónde.** `security/roles.py`, `services/` y `routes/`.

**Ataque que evita.** Que un usuario use funciones de otro rol o lea y modifique datos de otras personas.

**Cómo se prueba.** `tests/e2e/test_seguridad.py` (`test_cada_rol_recibe_403_en_lo_que_no_le_corresponde` prueba cada rol contra endpoints que no le corresponden, y `test_sin_token_las_rutas_protegidas_dan_401`), `tests/e2e/test_turnos.py` (`test_otro_paciente_no_puede_responder_el_turno`) y `tests/e2e/test_preferencias.py`.

## 7. Datos sensibles

**Qué hace.**
- Los serializadores ocultan campos internos (hash, intentos fallidos, bloqueo). La búsqueda de pacientes por DNI devuelve solo identificador, nombre y DNI. El paciente nunca ve una receta en borrador.
- Se registra en el log quién (identificador y rol) consulta datos de pacientes y recetas. El registro no guarda DNI, contenido clínico, contraseñas ni tokens. Solo se registran lecturas.
- Todas las respuestas llevan `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` y `Cache-Control: no-store`, para que no queden datos personales en cachés ni se pueda incrustar la API en otro sitio.
- Los registros de inicio de sesión tampoco incluyen contraseñas ni tokens.

**Dónde.** `utils/serializers.py`, `security/auditoria.py` (usado en `routes/pacientes.py` y `routes/recetas.py`), `security/headers.py` y `services/auth_service.py`.

**Ataque que evita.** Fuga de datos personales y clínicos, falta de trazabilidad ante un acceso indebido, clickjacking y adivinación del tipo de contenido.

**Cómo se prueba.** `tests/e2e/test_seguridad.py`: `test_encabezados_de_seguridad_en_todas_las_respuestas`, `test_se_registra_quien_consulta_pacientes`, `test_se_registra_el_acceso_a_las_recetas` y `test_los_logs_no_guardan_contrasenas_ni_tokens`.

## 8. Configuración y secretos

**Qué hace.**
- `SECRET_KEY` y `JWT_SECRET_KEY` se leen de variables de entorno. Si falta alguna, la aplicación no arranca y avisa cuál.
- Los orígenes permitidos por CORS se leen de `CORS_ORIGINS` (lista separada por comas). Solo esos orígenes reciben permiso del navegador.
- Los archivos `.env` no están en el repositorio. Se incluye `.env.example` con valores de ejemplo, sin datos reales.
- Las únicas claves escritas en el código son las de `TestConfig`, usadas solo en las pruebas.

**Dónde.** `config.py` (`lista_desde_env`, `validar_configuracion`, `TestConfig`), `__init__.py` y `.env.example`.

**Ataque que evita.** Filtrar claves al repositorio, arrancar en producción con claves vacías o conocidas, y aceptar pedidos de sitios no autorizados.

**Cómo se prueba.** `tests/unit/test_seguridad_config.py` y `tests/e2e/test_seguridad.py` (`test_la_app_no_arranca_sin_claves_secretas`, `test_cors_solo_permite_los_origenes_configurados`).

## 9. Cómo correr las pruebas

```
cd backend
uv run pytest -q
```

## 10. Límites conocidos y mejoras pendientes

- **HTTPS.** En desarrollo la aplicación corre por HTTP, así que las credenciales viajan sin cifrar. En un despliegue real debe ir detrás de HTTPS (TLS), por ejemplo con un proxy inverso, y en ese caso conviene agregar el encabezado `Strict-Transport-Security`. El análisis del tráfico con Wireshark está previsto para el Sprint 3.
- **Modo debug.** `run.py` inicia Flask con `debug=True`, válido solo para desarrollo. En producción debe desactivarse.
- **Límite de pedidos en memoria.** El contador se guarda en memoria del proceso: se reinicia con el servidor y no se comparte entre varios procesos. En producción debería usar un almacenamiento compartido, como Redis.
- **Token en el navegador.** El frontend guarda el token en `localStorage`, por lo que una vulnerabilidad XSS podría leerlo. Tampoco hay revocación: al cerrar sesión el token se descarta en el navegador, pero sigue siendo válido hasta que vence (30 minutos).
- **Cambios de rol.** El rol viaja dentro del token, así que un cambio de rol en la base recién se aplica al emitir un token nuevo.
- **Enumeración de cuentas.** El registro responde que el email ya está registrado, y el tiempo de respuesta del inicio de sesión difiere según exista o no la cuenta.
- **Registro de accesos.** Se escribe en el log estándar, no en una colección persistente, y no cubre todas las lecturas (por ejemplo, el listado de turnos del administrativo).
- **Documentación de la API.** Swagger está disponible sin autenticación en desarrollo y debería restringirse en producción.
- **Usuarios de demostración.** `utils/database.py` crea usuarios con contraseñas de ejemplo para la defensa. No deben usarse en un entorno real.
