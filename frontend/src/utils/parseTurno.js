// Convierte frases habladas en datos de un turno: especialidad, fecha y hora.
// Todo son funciones puras (sin navegador) para poder probarlas con node.

export const ESPECIALIDADES = [
  'Clínica médica',
  'Cardiología',
  'Traumatología',
  'Oftalmología',
  'Dermatología',
  'Ginecología',
  'Odontología',
  'Neurología',
  'Geriatría',
  'Kinesiología',
  'Otorrinolaringología',
  'Urología',
  'Endocrinología',
];

// palabra clave (sin tildes) -> especialidad
const CLAVES_ESPECIALIDAD = [
  [/clinic|cabecera|generalista|medico general/, 'Clínica médica'],
  [/cardio|corazon/, 'Cardiología'],
  [/traumat|huesos|fractura/, 'Traumatología'],
  [/oftalm|ojos|vista/, 'Oftalmología'],
  [/dermat|piel/, 'Dermatología'],
  [/gineco/, 'Ginecología'],
  [/odonto|dentista|muela|dientes/, 'Odontología'],
  [/neuro/, 'Neurología'],
  [/geriat/, 'Geriatría'],
  [/kinesi/, 'Kinesiología'],
  [/otorrino|oidos|garganta/, 'Otorrinolaringología'],
  [/urolog/, 'Urología'],
  [/endocrin|diabetes|tiroides/, 'Endocrinología'],
];

// Minúsculas, sin tildes; conserva dígitos, ":", "/" y "-"
export function limpiar(texto) {
  return (texto || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9ñ:/\-\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

const UNIDADES = {
  cero: 0, un: 1, uno: 1, una: 1, dos: 2, tres: 3, cuatro: 4, cinco: 5, seis: 6, siete: 7, ocho: 8, nueve: 9,
  diez: 10, once: 11, doce: 12, trece: 13, catorce: 14, quince: 15, dieciseis: 16, diecisiete: 17,
  dieciocho: 18, diecinueve: 19, veinte: 20, veintiuno: 21, veintiun: 21, veintidos: 22, veintitres: 23,
  veinticuatro: 24, veinticinco: 25, veintiseis: 26, veintisiete: 27, veintiocho: 28, veintinueve: 29,
  treinta: 30, cuarenta: 40, cincuenta: 50,
};
const DECENAS = { veinte: 20, treinta: 30, cuarenta: 40, cincuenta: 50 };

// "treinta y cinco" -> "35", "diez" -> "10" (el resto del texto queda igual)
export function palabrasADigitos(t) {
  let s = t.replace(
    /\b(veinte|treinta|cuarenta|cincuenta) y (uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve)\b/g,
    (_, d, u) => String(DECENAS[d] + UNIDADES[u]),
  );
  s = s.replace(new RegExp(`\\b(${Object.keys(UNIDADES).join('|')})\\b`, 'g'), (w) => String(UNIDADES[w]));
  return s;
}

export function buscarEspecialidad(texto) {
  const t = limpiar(texto);
  if (!t) return null;
  for (const [patron, nombre] of CLAVES_ESPECIALIDAD) {
    if (patron.test(t)) return nombre;
  }
  return null;
}

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const DIAS_SEMANA = { domingo: 0, lunes: 1, martes: 2, miercoles: 3, jueves: 4, viernes: 5, sabado: 6 };

const dos = (n) => String(n).padStart(2, '0');
const aIso = (d) => `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`;
const sumarDias = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);

// Devuelve 'YYYY-MM-DD' o null. Nunca devuelve una fecha anterior a hoy.
export function interpretarFecha(texto, ahora = new Date()) {
  let t = palabrasADigitos(limpiar(texto));
  t = t.split(/\ba las?\b|\ba la\b|\bhs\b|\bhoras\b/)[0]; // lo que viene después es la hora
  if (!t) return null;
  const hoy = new Date(ahora.getFullYear(), ahora.getMonth(), ahora.getDate());

  if (/\bpasado manana\b/.test(t)) return aIso(sumarDias(hoy, 2));
  if (/\bmanana\b/.test(t)) return aIso(sumarDias(hoy, 1));
  if (/\bhoy\b/.test(t)) return aIso(hoy);

  const valida = (y, m, d) => {
    const f = new Date(y, m, d);
    return f.getMonth() === m && f.getDate() === d ? f : null;
  };

  // "5 de noviembre", "5 noviembre"
  const conMes = t.match(new RegExp(`\\b(\\d{1,2})\\s*(?:de|del)?\\s*(${MESES.join('|')})\\b`));
  if (conMes) {
    const m = MESES.indexOf(conMes[2]);
    let f = valida(hoy.getFullYear(), m, Number(conMes[1]));
    if (f && f < hoy) f = valida(hoy.getFullYear() + 1, m, Number(conMes[1]));
    return f ? aIso(f) : null;
  }

  // "5/11" o "5-11"
  const barra = t.match(/\b(\d{1,2})[/-](\d{1,2})\b/);
  if (barra) {
    const m = Number(barra[2]) - 1;
    let f = valida(hoy.getFullYear(), m, Number(barra[1]));
    if (f && f < hoy) f = valida(hoy.getFullYear() + 1, m, Number(barra[1]));
    return f ? aIso(f) : null;
  }

  // "el lunes", "el próximo viernes": siempre la próxima vez que ocurre (nunca hoy)
  for (const [nombre, num] of Object.entries(DIAS_SEMANA)) {
    if (new RegExp(`\\b${nombre}\\b`).test(t)) {
      const falta = (num - hoy.getDay() + 7) % 7 || 7;
      return aIso(sumarDias(hoy, falta));
    }
  }

  // "el 5" / "día 12": este mes si todavía no pasó, si no el mes que viene
  const solo = t.match(/\b(\d{1,2})\b/);
  if (solo) {
    const d = Number(solo[1]);
    if (d < 1 || d > 31) return null;
    const f = valida(hoy.getFullYear(), hoy.getMonth(), d);
    if (f && f >= hoy) return aIso(f);
    const prox = valida(hoy.getFullYear(), hoy.getMonth() + 1, d);
    return prox ? aIso(prox) : null;
  }
  return null;
}

// Devuelve 'HH:MM' o null. Sin aclaración, de 1 a 7 se entiende como la tarde.
export function interpretarHora(texto) {
  let t = palabrasADigitos(limpiar(texto));
  if (!t) return null;
  if (/\bmedio ?dia\b/.test(t)) return '12:00';

  const despuesDeLas = t.match(/\b(?:a )?las? (\d.*)$/);
  if (despuesDeLas) t = despuesDeLas[1];

  let h;
  let m = 0;
  let r;
  if ((r = t.match(/\b(\d{1,2}) menos cuarto\b/))) {
    h = Number(r[1]) - 1;
    m = 45;
  } else if ((r = t.match(/\b(\d{1,2}) menos (\d{1,2})\b/))) {
    h = Number(r[1]) - 1;
    m = 60 - Number(r[2]);
  } else if ((r = t.match(/\b(\d{1,2}) y media\b/))) {
    h = Number(r[1]);
    m = 30;
  } else if ((r = t.match(/\b(\d{1,2}) y cuarto\b/))) {
    h = Number(r[1]);
    m = 15;
  } else if ((r = t.match(/\b(\d{1,2})[:.](\d{2})\b/)) || (r = t.match(/\b(\d{1,2}) y (\d{1,2})\b/))) {
    h = Number(r[1]);
    m = Number(r[2]);
  } else if ((r = t.match(/\b(\d{1,2})\b/))) {
    h = Number(r[1]);
  } else {
    return null;
  }

  const esTarde = /\b(tarde|noche)\b/.test(t);
  const esManana = /\b(manana|madrugada)\b/.test(t);
  if (esTarde && h < 12) h += 12;
  else if (!esTarde && !esManana && h >= 1 && h <= 7) h += 12;

  if (h < 0 || h > 23 || m < 0 || m > 59) return null;
  return `${dos(h)}:${dos(m)}`;
}

export function aFechaHora(fecha, hora) {
  const [y, mo, d] = fecha.split('-').map(Number);
  const [h, mi] = hora.split(':').map(Number);
  return new Date(y, mo - 1, d, h, mi);
}

// "2026-11-05", "10:30" -> "jueves 5 de noviembre a las 10 y 30"
export function describirFechaHora(fecha, hora) {
  const f = aFechaHora(fecha, hora);
  const dia = f.toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });
  const h = f.getHours();
  const m = f.getMinutes();
  const txt = m === 0 ? `${h} en punto` : `${h} y ${m < 10 ? 'cero ' : ''}${m}`;
  return `${dia} a las ${txt}`;
}

// El motivo es texto libre: se limpia y se pone mayúscula inicial. null si es muy corto.
export function limpiarMotivo(texto) {
  const t = (texto || '').trim().replace(/\s+/g, ' ');
  if (t.length < 3) return null;
  return t.charAt(0).toUpperCase() + t.slice(1, 300);
}
