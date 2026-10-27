# Patrones de diseño de App PAMI

El backend (Flask + MongoDB) usa cinco patrones de diseño. Para cada uno se indica **dónde está en el código**, **qué problema resuelve** y **por qué es adecuado** para esta aplicación.

| Patrón | Dónde está | Problema que resuelve |
|---|---|---|
| Repository | `backend/app/repositories/` | Separar las consultas a MongoDB de la lógica de negocio |
| Observer | `backend/app/patterns/observer.py` y `observers.py` | Que un módulo avise lo que pasó sin conocer a quien reacciona (notificaciones) |
| State | `backend/app/patterns/turno_state.py` | Controlar qué cambios de estado de un turno están permitidos |
| Factory | `backend/app/patterns/documento_factory.py` y `create_app()` | Centralizar cómo se arman las recetas, las órdenes y la aplicación |
| Strategy | `backend/app/patterns/recordatorio_strategy.py` y `canal_strategy.py` | Cambiar las reglas de los recordatorios y el canal de aviso al familiar sin tocar los servicios |

## 1. Repository

**Dónde.** Una clase por colección en `backend/app/repositories/`: `TurnoRepository`, `UsuarioRepository`, `RecetaRepository`, `NotificacionRepository`, `AvisoTomaRepository`, `FamiliarRepository` y `MensajeFamiliarRepository`, todas sobre `BaseRepository`. Los servicios (`backend/app/services/`) reciben el repositorio por parámetro y nunca escriben una consulta de MongoDB.

```python
class TurnoService:
    def __init__(self, turnos_repo, event_bus=None):
        self.repo = turnos_repo          # no sabe si abajo hay MongoDB o mongomock
```

**Problema.** Si las consultas están mezcladas con las reglas de negocio, cambiar un filtro obliga a tocar la lógica, y probar la lógica obliga a tener una base real.

**Por qué es adecuado.**
- Las consultas quedan en un solo lugar. Por ejemplo, `TurnoRepository.horario_ocupado` y `listar_confirmados_entre` se escriben una vez y se usan desde varios servicios.
- Los repositorios de turnos, recetas y notificaciones traducen los errores de la base: un id mal formado en la URL devuelve "no existe" (`InvalidId` se convierte en `None`) en lugar de un error 500.
- Las pruebas unitarias usan `mongomock` a través de los mismos repositorios, sin levantar MongoDB.
- El repositorio también esconde detalles de la base: `AvisoTomaRepository.registrar` devuelve `False` si el aviso de toma ya existía (lo garantiza un índice único), y el servicio de tomas no sabe cómo.

**Pruebas.** `tests/unit/test_turno_repository.py` y todos los tests de servicios.

## 2. Observer

**Dónde.** `EventBus` en `backend/app/patterns/observer.py` (con los nombres de los eventos) y los observers en `backend/app/patterns/observers.py`, que se suscriben una sola vez desde `create_app()`. Los servicios `TurnoService`, `TurnoAdminService` y `RecetaService` publican eventos.

| Evento | Lo publica | Qué hace el observer |
|---|---|---|
| `turno.otorgado` | `TurnoAdminService.otorgar` | Avisa al paciente la fecha y hora, y al familiar autorizado (si hay) |
| `turno.reprogramado` | `TurnoAdminService.reprogramar` | Avisa al paciente la nueva fecha para que la acepte o la rechace, y al familiar autorizado |
| `turno.cancelado` | `TurnoAdminService.cancelar` | Avisa al paciente que se canceló, y al familiar autorizado |
| `turno.confirmado` / `turno.rechazado` | `TurnoService` | Avisa al administrativo que otorgó el turno qué respondió el paciente; si confirmó, también al familiar autorizado |
| `turno.recordatorio` | `RecordatorioService.procesar` | Avisa al familiar autorizado que se acerca el turno |

```python
# el servicio solo cuenta lo que pasó
self.bus.publicar(TURNO_CANCELADO, datos_evento(turno))

# y en otro lugar se decide qué hacer cuando pasa
bus.suscribir(TURNO_CANCELADO, notificar_turno_cancelado)
```

En el Sprint 3 se sumó el observer `avisar_al_familiar`, suscrito a cinco eventos (`EVENTOS_PARA_FAMILIAR`). Se agregó sin modificar ninguno de los servicios que publican esos eventos: solo `RecordatorioService` pasó a publicar `turno.recordatorio`.

**Problema.** Los turnos no deberían depender del módulo de notificaciones. Si `TurnoAdminService` llamara directamente a `NotificacionService`, cada aviso nuevo (SMS, mail, recordatorio) obligaría a modificar el código de turnos.

**Por qué es adecuado.**
- Agregar una reacción nueva es suscribir otra función; los servicios de turnos no se tocan.
- Un observer que falla no rompe la operación principal: `EventBus.publicar` registra el error y sigue. Cancelar un turno funciona aunque falle la notificación.
- El evento no se loguea con sus datos, porque pueden incluir información del paciente.
- El aviso al familiar fue la prueba: una funcionalidad nueva que escucha eventos existentes sin cambiar el código que los produce. Y si falla el envío, el turno se otorga igual (hay una prueba que lo comprueba).

**Pruebas.** `tests/unit/test_event_bus.py`, `tests/unit/test_turno_admin_cambios.py` (se publica el evento correcto y no se publica nada si la transición falla) `tests/e2e/test_notificaciones.py` y `tests/e2e/test_familiar_avisos.py` (el familiar recibe cada evento, y un envío roto no rompe la operación).

## 3. State

**Dónde.** `backend/app/patterns/turno_state.py`. Cada estado del turno es una clase que sabe a qué estado se puede pasar desde él.

```
SOLICITADO --otorgar--> OTORGADO
OTORGADO --confirmar--> CONFIRMADO
OTORGADO --rechazar---> RECHAZADO
OTORGADO / CONFIRMADO / REPROGRAMADO --reprogramar--> REPROGRAMADO
REPROGRAMADO --confirmar--> CONFIRMADO
REPROGRAMADO --rechazar---> RECHAZADO
OTORGADO / CONFIRMADO / REPROGRAMADO --cancelar-----> CANCELADO
RECHAZADO y CANCELADO son estados finales
```

```python
nuevo_estado = estado_de(turno["estado"]).cancelar()   # lanza TransicionInvalida si no corresponde
```

**Problema.** Sin el patrón, cada servicio necesitaría una cadena de `if estado == ...` para saber si una acción es válida, y las reglas quedarían repetidas y desparejas.

**Por qué es adecuado.**
- Las reglas del flujo viven en un solo archivo. Cuando en el Sprint 2 se agregaron *reprogramar* y *cancelar*, las transiciones nuevas se escribieron solo ahí y los servicios solo piden la acción.
- Una acción inválida (por ejemplo cancelar un turno rechazado) lanza `TransicionInvalida`, que la API traduce a un error 409 con un mensaje claro.

**Pruebas.** `tests/unit/test_turno_state.py` (todas las transiciones válidas e inválidas) y los e2e que comprueban el 409.

## 4. Factory

**Dónde.**
- `DocumentoFactory` en `backend/app/patterns/documento_factory.py` crea recetas y órdenes (`crear_receta`, `crear_orden` y `crear`, que elige según el tipo). Lo usa `RecetaService`.
- `create_app()` en `backend/app/__init__.py` es la fábrica de la aplicación Flask: recibe la configuración y, opcionalmente, la base de datos.

**Problema.** Una receta lleva medicamentos y una orden no. Si cada lugar que las crea decidiera qué campos corresponden, se repetirían reglas y habría documentos inconsistentes. Con la aplicación pasa algo parecido: si se crea en un módulo con configuración fija, no se puede probar con otra base.

**Por qué es adecuado.**
- Un solo lugar sabe cómo se arma cada documento; agregar un tipo nuevo (por ejemplo un certificado) es agregar un método.
- `create_app(TestConfig, db=mongomock...)` permite probar toda la API sin MongoDB real.

**Pruebas.** `tests/unit/test_receta_service.py` y `tests/conftest.py` (crea la app de pruebas).

## 5. Strategy

Se usa en dos lugares: las reglas de los recordatorios y los canales de aviso al familiar.

### 5.1 Reglas de recordatorio

**Dónde.** `backend/app/patterns/recordatorio_strategy.py`. La interfaz es `ReglaRecordatorio` y las estrategias son `Recordar24Horas` y `Recordar2Horas`. El contexto que las usa es `RecordatorioService` (`backend/app/services/recordatorio_service.py`).

```python
class ReglaRecordatorio(ABC):
    @abstractmethod
    def debe_recordar(self, fecha_turno, ahora) -> bool: ...

# el servicio aplica las reglas sin saber cuáles son
aplicables = [r for r in self.reglas if r.debe_recordar(turno["fecha_hora"], ahora)]
```

**Problema.** El momento de avisar un turno cambia según la necesidad (un día antes, dos horas antes, el día anterior a la mañana). Con `if/elif` dentro del servicio, cada regla nueva lo modifica.

**Por qué es adecuado.**
- Agregar una regla es crear una clase nueva; `RecordatorioService` no se modifica. Hay una prueba que lo demuestra con una regla propia (`RecordarConDosDias`).
- Las reglas se pueden elegir sin tocar código con la variable de entorno `RECORDATORIOS_REGLAS` (por ejemplo `24h,2h`).
- Cada regla se cumple una sola vez por turno: el servicio guarda en el turno qué reglas ya se aplicaron, así que se puede ejecutar todas las veces que se quiera sin duplicar avisos.

**Cómo se ejecuta.** Con el script programable `uv run python -m scripts.enviar_recordatorios`, con el botón *Generar recordatorios* del panel del administrativo o con `POST /api/recordatorios/ejecutar` (solo administrativo).

**Variables opcionales.** `RECORDATORIOS_REGLAS` (reglas a usar) y `RECORDATORIOS_UTC_OFFSET` (diferencia horaria de la hora local con UTC; por defecto `-3`, porque los turnos se guardan en hora local sin zona horaria).

**Pruebas.** `tests/unit/test_recordatorio_strategy.py`, `tests/unit/test_recordatorio_service.py` y `tests/e2e/test_recordatorios.py`.

### 5.2 Canal de aviso al familiar

**Dónde.** `backend/app/patterns/canal_strategy.py`. La interfaz es `CanalEnvio` y las estrategias son `CanalSMS` y `CanalEmail`. El contexto que las usa es `FamiliarService.avisar_turno` (`backend/app/services/familiar_service.py`).

```python
class CanalEnvio(ABC):
    @abstractmethod
    def enviar(self, familiar, texto) -> dict: ...   # devuelve canal, destino, asunto y texto

# el servicio usa el canal que eligió el paciente sin saber cuál es
entrega = canal_por_nombre(familiar["canal"], self.canales).enviar(familiar, texto)
```

**Problema.** Cada canal arma el mensaje de otra forma: un SMS no puede pasar de 160 caracteres y no tiene asunto; un email lleva asunto, saludo y una aclaración de por qué se lo recibe. Con `if canal == "sms"` dentro del servicio, cada canal nuevo (por ejemplo WhatsApp) lo modifica.

**Por qué es adecuado.**
- Agregar un canal es crear una clase con el mismo método. Hay pruebas que lo demuestran con un canal propio y con un canal falso inyectado en el servicio.
- El envío es **simulado**: el canal devuelve el mensaje tal como saldría y el servicio lo guarda en la bandeja de salida del paciente (`mensajes_familiar`), que el paciente ve en su pantalla. Con un proveedor real, solo cambiaría el cuerpo de `enviar`.
- El canal no conoce la base de datos y el servicio no conoce los canales concretos: cada uno se prueba por separado.

**Datos mínimos.** El texto lo arma `texto_para_familiar` con el nombre de pila, el día y la hora. Nunca lleva especialidad, motivo ni datos de recetas, y los avisos de toma de medicación no se envían al familiar.

**Pruebas.** `tests/unit/test_canal_strategy.py`, `tests/unit/test_familiar_avisos.py` y `tests/e2e/test_familiar_avisos.py`.

## Cómo trabajan juntos

Un ejemplo completo: el administrativo reprograma un turno.

1. La ruta `PATCH /api/turnos/<id>/reprogramar` valida el rol y el cuerpo, y llama a `TurnoAdminService.reprogramar`.
2. **State** comprueba que el turno se puede reprogramar y devuelve el nuevo estado.
3. **Repository** guarda la nueva fecha y el estado.
4. El servicio publica `turno.reprogramado` en el **Observer** (`EventBus`).
5. Un observer crea la notificación para el paciente.
6. Otro observer, `avisar_al_familiar`, mira si el paciente autorizó a un familiar. Si es así, el canal que eligió (**Strategy**) arma el mensaje con datos mínimos y queda en la bandeja de salida.
7. Más tarde, cuando el paciente confirma, el mismo turno pasa a confirmado y el recordatorio lo toma con **Strategy** (las reglas de 24 y 2 horas).

## Preguntas que pueden hacer en la defensa

- **¿Por qué Observer y no llamar directo a las notificaciones?** Para que turnos no dependa de notificaciones y para que un aviso fallido no rompa la operación.
- **¿Qué pasa si agrego un estado nuevo?** Se agrega una clase en `turno_state.py` y sus transiciones; los servicios no cambian.
- **¿Cómo se agrega una regla de recordatorio nueva?** Se crea una clase que hereda de `ReglaRecordatorio` y se la agrega a `REGLAS_DISPONIBLES`.
- **¿Para qué sirve el Repository si ya usamos MongoDB?** Para tener las consultas en un lugar y poder probar la lógica con `mongomock`.
- **¿Cómo se agrega un canal de aviso nuevo?** Se crea una clase que hereda de `CanalEnvio` y se la suma a `CANALES`; el servicio de familiares no cambia.
- **¿Por qué el aviso al familiar es simulado?** Porque no hay un proveedor real de SMS ni de email en el proyecto. La estrategia deja la interfaz lista y el paciente ve en pantalla qué se enviaría.
- **¿Qué datos se comparten con el familiar?** Solo el nombre de pila, que es un turno médico, y el día y la hora, y solo si el paciente dio su consentimiento. No se comparte especialidad, motivo, recetas ni medicación.
- **¿Qué diferencia hay entre State y Strategy?** En State el objeto cambia de comportamiento según su estado y las transiciones son parte del flujo; en Strategy se elige entre algoritmos intercambiables y no hay "estado actual".
