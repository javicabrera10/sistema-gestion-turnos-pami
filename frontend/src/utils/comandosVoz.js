// Interpreta lo que dijo la persona y lo convierte en una intención.
// Es una función pura (sin navegador) para poder probarla fácil.

export const INTENCION = {
  ACEPTAR: 'aceptar',
  RECHAZAR: 'rechazar',
  REPETIR: 'repetir',
  SIGUIENTE: 'siguiente',
  SALIR: 'salir',
  SI: 'si',
  NO: 'no',
  NADA: 'nada',
};

export function normalizar(texto) {
  return (texto || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-zñ\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

const tiene = (t, patrones) => patrones.some((p) => p.test(t));

// contexto 'accion': esperamos aceptar / rechazar / repetir / siguiente / salir
// contexto 'confirmacion': esperamos sí / no
export function interpretar(texto, contexto = 'accion') {
  // El reconocimiento puede devolver varias alternativas separadas por "|"
  const alternativas = (texto || '').split('|').map(normalizar).filter(Boolean);
  if (alternativas.length === 0) return INTENCION.NADA;

  for (const t of alternativas) {
    const r = interpretarUna(t, contexto);
    if (r !== INTENCION.NADA) return r;
  }
  return INTENCION.NADA;
}

function interpretarUna(t, contexto) {
  if (tiene(t, [/\b(salir|parar|para|basta|termin\w*|detener|detene|chau|cerrar)\b/])) {
    return INTENCION.SALIR;
  }

  if (contexto === 'confirmacion') {
    if (tiene(t, [/^no\b/, /\bno (quiero|confirmo|gracias)\b/, /\b(cancelar|cancela|equivoque|mal)\b/])) {
      return INTENCION.NO;
    }
    if (tiene(t, [/^si\b/, /\b(confirmo|confirmar|dale|correcto|ok|okey|claro|exacto|seguro)\b/])) {
      return INTENCION.SI;
    }
    return INTENCION.NADA;
  }

  // "no acepto" contiene "acepto": el rechazo se revisa primero
  if (tiene(t, [/\brechaz\w*/, /\bno (acepto|aceptar|quiero|me sirve|puedo|voy)\b/, /\bno\b.*\bturno\b/])) {
    return INTENCION.RECHAZAR;
  }
  if (tiene(t, [/\bacept\w*/, /\bconfirm\w*/, /\bsi\b/, /\b(dale|ok|okey|de acuerdo|me sirve|perfecto)\b/])) {
    return INTENCION.ACEPTAR;
  }
  if (tiene(t, [/\brepet\w*/, /\bde nuevo\b/, /\botra vez\b/, /\bno entend\w*/, /\bmas despacio\b/])) {
    return INTENCION.REPETIR;
  }
  if (tiene(t, [/\bsiguiente\b/, /\bproxim\w*/, /\bpasar\b/, /\bsaltar\b/, /\bmas tarde\b/, /\bdespues\b/])) {
    return INTENCION.SIGUIENTE;
  }
  return INTENCION.NADA;
}
