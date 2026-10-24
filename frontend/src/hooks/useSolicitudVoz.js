import { useCallback, useEffect, useRef, useState } from 'react';
import { callar, cancelarEscucha, escuchar, hablar } from '../services/voz';
import { INTENCION, esOrdenDeSalir, interpretar } from '../utils/comandosVoz';
import {
  aFechaHora,
  buscarEspecialidad,
  describirFechaHora,
  interpretarFecha,
  interpretarHora,
  limpiarMotivo,
} from '../utils/parseTurno';

export const ESTADO = { QUIETO: 'quieto', HABLANDO: 'hablando', ESCUCHANDO: 'escuchando', ENVIANDO: 'enviando' };

const INTENTOS = 2;

// Guía por voz para pedir un turno: pregunta especialidad, día, hora y motivo,
// completa el formulario, lee el resumen y envía si la persona dice "sí".
//
// datos:     { especialidad, fecha, hora, motivo } (lo que ya hay en el formulario)
// setCampo:  (campo, valor) => void
// enviar:    async () => void (hace el POST; tira Error si falla)
export function useSolicitudVoz({ datos, setCampo, enviar }) {
  const [estado, setEstado] = useState(ESTADO.QUIETO);
  const [activo, setActivo] = useState(false);
  const [mensaje, setMensaje] = useState('');
  const [oido, setOido] = useState('');
  const [aviso, setAviso] = useState('');

  const sesion = useRef(0);
  const datosRef = useRef(datos);
  const enviarRef = useRef(enviar);
  const setRef = useRef(setCampo);
  useEffect(() => {
    datosRef.current = datos;
    enviarRef.current = enviar;
    setRef.current = setCampo;
  });

  const detener = useCallback(() => {
    sesion.current += 1;
    callar();
    cancelarEscucha();
    setActivo(false);
    setEstado(ESTADO.QUIETO);
  }, []);

  useEffect(() => detener, [detener]); // al salir de la pantalla, callar todo

  const decir = useCallback(async (texto, vigente) => {
    if (!vigente()) return;
    setMensaje(texto);
    setEstado(ESTADO.HABLANDO);
    await hablar(texto);
  }, []);

  // Hace la pregunta y escucha. `leer` convierte cada alternativa en un valor (o null).
  // Devuelve { valor, texto } | { salir: true } | null (no se entendió) | { error }
  const preguntar = useCallback(
    async (pregunta, leer, vigente) => {
      for (let i = 0; i < INTENTOS; i += 1) {
        await decir(i === 0 ? pregunta : `No te entendí. ${pregunta}`, vigente);
        if (!vigente()) return { salir: true };
        await new Promise((r) => setTimeout(r, 400)); // que no se escuche a sí mismo
        if (!vigente()) return { salir: true };
        setEstado(ESTADO.ESCUCHANDO);
        setOido('');
        let texto;
        try {
          texto = await escuchar({ tiempoMs: 9000 });
        } catch (e) {
          if (!vigente()) return { salir: true };
          return {
            error:
              e.message === 'permiso-denegado'
                ? 'El micrófono está bloqueado. Completá el formulario a mano.'
                : 'Este navegador no permite hablar con la aplicación. Completá el formulario a mano.',
          };
        }
        if (!vigente()) return { salir: true };
        const alternativas = texto.split('|').map((a) => a.trim()).filter(Boolean);
        setOido(alternativas[0] || '');
        if (alternativas.some(esOrdenDeSalir)) return { salir: true };
        for (const alt of alternativas) {
          const valor = leer(alt);
          if (valor) return { valor, texto: alt };
        }
      }
      return null;
    },
    [decir],
  );

  const iniciar = useCallback(async () => {
    const id = ++sesion.current;
    const vigente = () => sesion.current === id;
    callar();
    cancelarEscucha();
    setActivo(true);
    setAviso('');

    const d = { ...datosRef.current };
    const poner = (campo, valor) => {
      d[campo] = valor;
      setRef.current(campo, valor);
    };
    const cortar = async (texto) => {
      if (!vigente()) return;
      await decir(texto, vigente);
      if (vigente()) detener();
    };

    // Cada paso: [campo, pregunta, lector, frase al anotar]
    const pasos = [
      ['especialidad', '¿Para qué especialidad querés el turno? Por ejemplo, cardiología o clínica médica.', buscarEspecialidad, (v) => `Anoté ${v}.`],
      ['fecha', '¿Qué día te queda bien? Podés decir mañana, el lunes, o el 5 de noviembre.', (t) => interpretarFecha(t), null],
      ['hora', '¿A qué hora? Por ejemplo, 10 y media de la mañana.', interpretarHora, null],
      ['motivo', '¿Cuál es el motivo de la consulta?', limpiarMotivo, (v) => `Anoté: ${v}.`],
    ];

    for (const [campo, pregunta, leer, frase] of pasos) {
      if (d[campo]) continue; // ya estaba completo en el formulario
      const r = await preguntar(pregunta, leer, vigente);
      if (!vigente()) return;
      if (r?.salir) return cortar('Listo, me quedo en silencio.');
      if (r?.error) {
        setAviso(r.error);
        return cortar(r.error);
      }
      if (!r) return cortar('No pude entenderte. Podés completar los datos en la pantalla.');
      poner(campo, r.valor);
      if (campo === 'fecha' && !d.hora && /\b(a )?las? \d|:\d{2}|\bhs\b/.test(r.texto.toLowerCase())) {
        // dijo día y hora en la misma frase: "el lunes a las 10"
        const h = interpretarHora(r.texto);
        if (h) poner('hora', h);
      }
      if (frase) await decir(frase(r.valor), vigente);
    }
    if (!vigente()) return;

    if (aFechaHora(d.fecha, d.hora) <= new Date()) {
      return cortar('Esa fecha y hora ya pasaron. Corregí el día o la hora en la pantalla.');
    }

    const resumen =
      `Voy a pedir un turno de ${d.especialidad} para el ${describirFechaHora(d.fecha, d.hora)}. ` +
      `Motivo: ${d.motivo}. ¿Lo envío? Decí sí o no.`;
    const conf = await preguntar(resumen, (t) => {
      const i = interpretar(t, 'confirmacion');
      return i === INTENCION.SI || i === INTENCION.NO ? i : null;
    }, vigente);
    if (!vigente()) return;
    if (conf?.salir) return cortar('Listo, no envié nada.');
    if (conf?.valor !== INTENCION.SI) {
      return cortar('Está bien, no lo envié. Podés corregir los datos en la pantalla.');
    }

    setEstado(ESTADO.ENVIANDO);
    try {
      await enviarRef.current();
      await cortar('Listo. Pedí tu turno. Te vamos a avisar cuando te lo otorguen.');
    } catch (e) {
      await cortar(`No pude enviar el turno. ${e.message || ''}`);
    }
  }, [decir, detener, preguntar]);

  return { estado, activo, mensaje, oido, aviso, iniciar, detener };
}
