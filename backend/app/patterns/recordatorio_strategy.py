"""Patrón Strategy: reglas de recordatorio intercambiables.

Cada regla responde una sola pregunta: "¿hay que avisarle al paciente ahora de este turno?".
El servicio de recordatorios recibe una lista de reglas y las aplica sin saber cuáles son, así que
agregar una regla nueva (por ejemplo "el día anterior") o quitar una no obliga a tocar el servicio.

Reglas disponibles:
    "24h"  avisa cuando faltan 24 horas o menos para el turno
    "2h"   avisa cuando faltan 2 horas o menos para el turno
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta


class ReglaRecordatorio(ABC):
    # Identifica la regla: se guarda en el turno para no repetir el mismo aviso
    nombre: str
    # Hasta cuántas horas antes del turno puede aplicar la regla (el servicio lo usa para acotar la búsqueda)
    horas_antes: int

    @abstractmethod
    def debe_recordar(self, fecha_turno: datetime, ahora: datetime) -> bool:
        """True si, a esta hora, corresponde recordar un turno que es en `fecha_turno`."""


def _faltan_como_maximo(fecha_turno: datetime, ahora: datetime, horas: int) -> bool:
    # el turno todavía no pasó y falta `horas` o menos
    return ahora < fecha_turno <= ahora + timedelta(hours=horas)


class Recordar24Horas(ReglaRecordatorio):
    nombre = "24h"
    horas_antes = 24

    def debe_recordar(self, fecha_turno: datetime, ahora: datetime) -> bool:
        return _faltan_como_maximo(fecha_turno, ahora, 24)


class Recordar2Horas(ReglaRecordatorio):
    nombre = "2h"
    horas_antes = 2

    def debe_recordar(self, fecha_turno: datetime, ahora: datetime) -> bool:
        return _faltan_como_maximo(fecha_turno, ahora, 2)


REGLAS_DISPONIBLES = {r.nombre: r for r in (Recordar24Horas, Recordar2Horas)}

# Por defecto se usan las dos, de la más urgente a la menos urgente
REGLAS_POR_DEFECTO = (Recordar2Horas(), Recordar24Horas())


def reglas_desde_nombres(texto: str) -> tuple[ReglaRecordatorio, ...]:
    """Arma las reglas a partir de un texto como "24h,2h" (para elegirlas sin tocar el código)."""
    reglas = []
    for nombre in (n.strip() for n in texto.split(",")):
        if not nombre:
            continue
        if nombre not in REGLAS_DISPONIBLES:
            raise ValueError(f"Regla de recordatorio desconocida: {nombre!r}")
        reglas.append(REGLAS_DISPONIBLES[nombre]())
    # siempre de la más urgente a la menos urgente
    return tuple(sorted(reglas, key=lambda r: r.horas_antes))
