// Capa fina sobre la Web Speech API (síntesis y reconocimiento de voz).
// Funciona en Chrome/Edge/Safari; Firefox no trae reconocimiento, por eso
// la UI siempre ofrece botones como alternativa.

const synth = typeof window !== 'undefined' ? window.speechSynthesis : null;
const RecognitionAPI =
  typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null;

export const sintesisSoportada = Boolean(synth);
export const reconocimientoSoportado = Boolean(RecognitionAPI);

function elegirVoz() {
  const voces = synth.getVoices();
  const prioridad = ['es-AR', 'es-419', 'es-US', 'es-MX', 'es-ES', 'es'];
  for (const lang of prioridad) {
    const voz = voces.find((v) => v.lang.replace('_', '-').toLowerCase().startsWith(lang.toLowerCase()));
    if (voz) return voz;
  }
  return null;
}

// Habla un texto y resuelve cuando termina (o si falla: nunca rechaza).
export function hablar(texto, { velocidad = 0.9 } = {}) {
  if (!sintesisSoportada || !texto) return Promise.resolve();
  return new Promise((resolve) => {
    synth.cancel();
    const u = new SpeechSynthesisUtterance(texto);
    const voz = elegirVoz();
    if (voz) u.voice = voz;
    u.lang = voz?.lang || 'es-AR';
    u.rate = velocidad;
    // Red de seguridad: algunos navegadores no disparan "end" si se cancela la voz.
    const limite = setTimeout(resolve, Math.max(4000, texto.length * 110));
    const terminar = () => {
      clearTimeout(limite);
      resolve();
    };
    u.onend = terminar;
    u.onerror = terminar;
    synth.speak(u);
  });
}

export function callar() {
  if (sintesisSoportada) synth.cancel();
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

// Escucha una frase. Resuelve con el texto ('' si no se dijo nada).
// Rechaza con Error('permiso-denegado') si el usuario bloqueó el micrófono.
export function escuchar({ tiempoMs = 8000 } = {}) {
  if (!reconocimientoSoportado) return Promise.reject(new Error('no-soportado'));
  cancelarEscucha();
  return new Promise((resolve, reject) => {
    const rec = new RecognitionAPI();
    reconocimientoActivo = rec;
    rec.lang = 'es-AR';
    rec.interimResults = false;
    rec.maxAlternatives = 3;
    rec.continuous = false;

    let texto = '';
    let listo = false;
    const fin = (fn, valor) => {
      if (listo) return;
      listo = true;
      clearTimeout(corte);
      if (reconocimientoActivo === rec) reconocimientoActivo = null;
      fn(valor);
    };
    const corte = setTimeout(() => {
      try {
        rec.stop();
      } catch {
        /* nada */
      }
    }, tiempoMs);

    rec.onresult = (e) => {
      const alternativas = Array.from(e.results[0] || []).map((a) => a.transcript);
      texto = alternativas.join(' | ');
    };
    rec.onerror = (e) => {
      if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
        fin(reject, new Error('permiso-denegado'));
      } else if (e.error === 'aborted') {
        fin(resolve, '');
      } else {
        // no-speech, audio-capture, network...: se trata como "no escuché nada"
        fin(resolve, '');
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
