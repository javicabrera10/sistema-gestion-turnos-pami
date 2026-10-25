// Capa fina sobre la Web Speech API (síntesis y reconocimiento de voz).
// Funciona en Chrome/Edge/Safari; Firefox no trae reconocimiento, por eso
// la UI siempre ofrece botones como alternativa.

const synth = typeof window !== 'undefined' ? window.speechSynthesis : null;
const RecognitionAPI =
  typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

export const sintesisSoportada = Boolean(synth);
export const reconocimientoSoportado = Boolean(RecognitionAPI);

const pausa = (ms) => new Promise((resolve) => { setTimeout(resolve, ms); });

// Chrome carga la lista de voces de forma asíncrona: la primera vez puede venir vacía.
function cargarVoces() {
  return new Promise((resolve) => {
    const ya = synth.getVoices();
    if (ya.length > 0) {
      resolve(ya);
      return;
    }
    const listo = () => {
      synth.removeEventListener('voiceschanged', listo);
      resolve(synth.getVoices());
    };
    synth.addEventListener('voiceschanged', listo);
    setTimeout(listo, 1000);
  });
}

function elegirVoz(voces) {
  const prioridad = ['es-AR', 'es-419', 'es-US', 'es-MX', 'es-ES', 'es'];
  for (const lang of prioridad) {
    const voz = voces.find((v) => v.lang.replace('_', '-').toLowerCase().startsWith(lang.toLowerCase()));
    if (voz) return voz;
  }
  return null;
}

// Cambia cada vez que se manda a callar o se empieza a hablar de nuevo: corta lo que quedaba pendiente.
let marca = 0;

// Habla UNA frase y resuelve cuando termina de verdad (o si falla: nunca rechaza).
function hablarFrase(frase, voz, velocidad) {
  return new Promise((resolve) => {
    const u = new SpeechSynthesisUtterance(frase);
    if (voz) u.voice = voz;
    u.lang = voz?.lang || 'es-AR';
    u.rate = velocidad;

    let listo = false;
    let empezo = false;
    const terminar = () => {
      if (listo) return;
      listo = true;
      clearInterval(vigilante);
      clearTimeout(limite);
      resolve();
    };
    // Red de seguridad por si el navegador nunca avisa que terminó
    const limite = setTimeout(terminar, Math.max(6000, frase.length * 200));
    // Algunos navegadores no disparan "end": se revisa si ya dejó de hablar
    const vigilante = setInterval(() => {
      if (empezo && !synth.speaking && !synth.pending) terminar();
    }, 250);

    u.onstart = () => { empezo = true; };
    u.onend = terminar;
    u.onerror = terminar;
    synth.speak(u);
  });
}

// Habla un texto frase por frase (Chrome corta las frases largas) y resuelve al terminar.
export async function hablar(texto, { velocidad = 0.9 } = {}) {
  if (!sintesisSoportada || !texto) return;
  try {
    marca += 1;
    const mia = marca;
    synth.cancel();
    await pausa(60); // Chrome ignora un speak() que llega pegado a un cancel()
    const voces = await cargarVoces();
    if (mia !== marca) return;
    const voz = elegirVoz(voces);
    const frases = texto.split(/(?<=[.!?])\s+/).map((f) => f.trim()).filter(Boolean);
    for (const frase of frases) {
      if (mia !== marca) return;
      await hablarFrase(frase, voz, velocidad);
    }
  } catch {
    /* si la síntesis falla, la app sigue funcionando con los botones */
  }
}

export function callar() {
  marca += 1;
  if (sintesisSoportada) synth.cancel();
}

// Pide el permiso del micrófono al empezar (antes de la primera pregunta).
// Devuelve null si está todo bien, o 'permiso-denegado' / 'sin-microfono'.
export async function pedirMicrofono() {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) return null;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach((t) => t.stop());
    return null;
  } catch (e) {
    if (e?.name === 'NotFoundError' || e?.name === 'DevicesNotFoundError') return 'sin-microfono';
    if (e?.name === 'NotAllowedError' || e?.name === 'SecurityError') return 'permiso-denegado';
    return null; // otro motivo: se deja que el reconocimiento lo intente igual
  }
}

let reconocimientoActivo = null;

export function cancelarEscucha() {
  if (reconocimientoActivo) {
    try {
      reconocimientoActivo.abort();
    } catch {
      /* ya estaba detenido */
    }
    reconocimientoActivo = null;
  }
}

// Junta lo que se dijo. Devuelve alternativas separadas por " | " (la más probable primero).
function armarTexto(resultados) {
  const segmentos = Array.from(resultados);
  if (segmentos.length === 0) return '';
  const previos = segmentos.slice(0, -1).map((s) => s[0].transcript.trim()).join(' ');
  const ultimo = Array.from(segmentos[segmentos.length - 1]);
  return ultimo.map((a) => `${previos} ${a.transcript}`.trim()).join(' | ');
}

// Escucha una frase. Resuelve con el texto ('' si no se dijo nada).
// Termina cuando hay una pausa de `pausaMs` después de hablar, si no se dice nada en `esperaMs`,
// o a los `tiempoMs` como máximo. `alEscuchar` se llama cuando el micrófono ya está abierto.
// Rechaza con Error: 'permiso-denegado', 'sin-microfono', 'sin-red' o 'no-soportado'.
export function escuchar({ tiempoMs = 15000, esperaMs = 8000, pausaMs = 1400, alEscuchar } = {}) {
  if (!reconocimientoSoportado) return Promise.reject(new Error('no-soportado'));
  cancelarEscucha();
  return new Promise((resolve, reject) => {
    const rec = new RecognitionAPI();
    reconocimientoActivo = rec;
    rec.lang = 'es-AR';
    rec.interimResults = true;
    rec.maxAlternatives = 3;
    rec.continuous = true;

    let texto = '';
    let listo = false;
    let avisado = false;
    let tEspera = null;
    let tMaximo = null;
    let tPausa = null;

    const cortar = () => {
      try {
        rec.stop();
      } catch {
        /* ya estaba detenido */
      }
    };
    const avisar = () => {
      if (avisado) return;
      avisado = true;
      if (alEscuchar) alEscuchar();
    };
    const fin = (fn, valor) => {
      if (listo) return;
      listo = true;
      clearTimeout(tEspera);
      clearTimeout(tMaximo);
      clearTimeout(tPausa);
      if (reconocimientoActivo === rec) reconocimientoActivo = null;
      fn(valor);
    };

    rec.onstart = () => {
      tEspera = setTimeout(cortar, esperaMs);
      tMaximo = setTimeout(cortar, tiempoMs);
      setTimeout(avisar, 800); // por si el navegador no avisa cuando abre el micrófono
    };
    rec.onaudiostart = avisar;
    rec.onresult = (e) => {
      avisar();
      texto = armarTexto(e.results);
      clearTimeout(tEspera);
      clearTimeout(tPausa);
      tPausa = setTimeout(cortar, pausaMs); // si hace una pausa larga, se da por terminada la frase
    };
    rec.onerror = (e) => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        fin(reject, new Error('permiso-denegado'));
      } else if (e.error === 'audio-capture') {
        fin(reject, new Error('sin-microfono'));
      } else if (e.error === 'network') {
        fin(reject, new Error('sin-red'));
      } else {
        // no-speech, aborted...: se trata como "no escuché nada"
        fin(resolve, e.error === 'aborted' ? '' : texto);
      }
    };
    rec.onend = () => fin(resolve, texto);

    try {
      rec.start();
    } catch {
      fin(resolve, '');
    }
  });
}