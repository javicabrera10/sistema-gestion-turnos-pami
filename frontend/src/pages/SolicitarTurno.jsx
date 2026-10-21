import { useCallback, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import { reconocimientoSoportado, sintesisSoportada } from '../services/voz';
import { ESTADO, useSolicitudVoz } from '../hooks/useSolicitudVoz';
import { ESPECIALIDADES } from '../utils/parseTurno';
import '../styles/solicitud.css';

// El contrato del Sprint 1 agrega `origen: "manual" | "voz"` a la solicitud (tarea J4).
// El backend actual usa extra="forbid" y todavía lo rechaza: poner en true cuando Javier lo agregue.
const ENVIAR_ORIGEN = false;

const ETIQUETA = {
  [ESTADO.QUIETO]: 'Podés pedir el turno hablando',
  [ESTADO.HABLANDO]: 'Hablando…',
  [ESTADO.ESCUCHANDO]: 'Te escucho, hablá ahora',
  [ESTADO.ENVIANDO]: 'Enviando tu pedido…',
};

const VACIO = { especialidad: '', fecha: '', hora: '', motivo: '' };
const hoyIso = () => {
  const h = new Date();
  return `${h.getFullYear()}-${String(h.getMonth() + 1).padStart(2, '0')}-${String(h.getDate()).padStart(2, '0')}`;
};

export default function SolicitarTurno() {
  const [datos, setDatos] = useState(VACIO);
  const [error, setError] = useState('');
  const [creado, setCreado] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const datosRef = useRef(datos);
  const usoVoz = useRef(false);

  const setCampo = useCallback((campo, valor) => {
    setDatos((prev) => {
      const nuevo = { ...prev, [campo]: valor };
      datosRef.current = nuevo;
      return nuevo;
    });
  }, []);

  // Se usa tanto desde el botón como desde la voz (lee siempre los datos más recientes)
  const enviar = useCallback(async () => {
    const d = datosRef.current;
    const cuerpo = {
      especialidad: d.especialidad,
      fecha_hora: `${d.fecha}T${d.hora}:00`, // hora local, igual que el resto de la app
      motivo: d.motivo,
    };
    if (ENVIAR_ORIGEN) cuerpo.origen = usoVoz.current ? 'voz' : 'manual';
    setEnviando(true);
    setError('');
    try {
      setCreado(await api.post('/turnos', cuerpo));
    } catch (e) {
      setError(e.message);
      throw e;
    } finally {
      setEnviando(false);
    }
  }, []);

  const voz = useSolicitudVoz({ datos, setCampo, enviar });

  const alEnviarManual = async (e) => {
    e.preventDefault();
    voz.detener();
    try {
      await enviar();
    } catch {
      /* el error ya quedó en pantalla */
    }
  };

  const empezarVoz = () => {
    usoVoz.current = true;
    voz.iniciar();
  };

  if (creado) {
    return (
      <main className="sol-pagina">
        <h1>¡Pedido enviado!</h1>
        <p className="sol-ok" role="status">
          Pediste un turno de <strong>{creado.especialidad}</strong>. Te vamos a avisar cuando te lo otorguen.
        </p>
        <div className="sol-acciones">
          <button type="button" className="sol-principal" onClick={() => { setCreado(null); setDatos(VACIO); datosRef.current = VACIO; usoVoz.current = false; }}>
            Pedir otro turno
          </button>
          <Link to="/paciente" className="sol-link">Volver al inicio</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="sol-pagina">
      <Link to="/paciente" className="sol-link">← Inicio</Link>
      <h1>Pedir un turno</h1>

      <section className="sol-voz" aria-labelledby="sol-voz-titulo">
        <h2 id="sol-voz-titulo">Pedirlo con la voz</h2>
        {!sintesisSoportada || !reconocimientoSoportado ? (
          <p className="sol-alerta" role="status">
            Este navegador no permite pedir el turno hablando. Completá el formulario de abajo
            (la voz funciona en Chrome o Edge).
          </p>
        ) : (
          <>
            <div className={`sol-estado sol-estado--${voz.estado}`} role="status" aria-live="polite">
              <span className="sol-punto" aria-hidden="true" />
              {ETIQUETA[voz.estado]}
            </div>
            {voz.activo && voz.mensaje && <p className="sol-subtitulo">“{voz.mensaje}”</p>}
            {voz.activo && voz.oido && <p>Entendí: <strong>{voz.oido}</strong></p>}
            {voz.aviso && <p className="sol-alerta" role="alert">{voz.aviso}</p>}
            {!voz.activo ? (
              <button type="button" className="sol-principal" onClick={empezarVoz}>🎤 Pedir turno hablando</button>
            ) : (
              <button type="button" className="sol-peligro" onClick={voz.detener}>⏹ Parar</button>
            )}
            <p className="sol-ayuda">Te voy a preguntar: especialidad, día, hora y motivo. Podés decir “parar” cuando quieras.</p>
          </>
        )}
      </section>

      <form className="sol-form" onSubmit={alEnviarManual}>
        <h2>Datos del turno</h2>
        <label>
          Especialidad
          <select value={datos.especialidad} onChange={(e) => setCampo('especialidad', e.target.value)} required>
            <option value="">Elegí una…</option>
            {ESPECIALIDADES.map((esp) => <option key={esp} value={esp}>{esp}</option>)}
          </select>
        </label>
        <label>
          Día
          <input type="date" min={hoyIso()} value={datos.fecha} onChange={(e) => setCampo('fecha', e.target.value)} required />
        </label>
        <label>
          Hora
          <input type="time" value={datos.hora} onChange={(e) => setCampo('hora', e.target.value)} required />
        </label>
        <label>
          Motivo de la consulta
          <textarea rows={3} minLength={3} maxLength={300} value={datos.motivo} onChange={(e) => setCampo('motivo', e.target.value)} required />
        </label>

        {error && <p className="sol-alerta" role="alert">{error}</p>}
        <button type="submit" className="sol-principal" disabled={enviando}>
          {enviando ? 'Enviando…' : 'Solicitar turno'}
        </button>
      </form>
    </main>
  );
}
