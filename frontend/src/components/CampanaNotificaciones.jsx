import { useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import '../styles/notificaciones.css';

// Ícono según el "tipo" que manda el backend; si llega un tipo nuevo se muestra la campana
const ICONOS = {
  turno_otorgado: '📅',
  turno_reprogramado: '🔄',
  turno_cancelado: '❌',
  turno_confirmado: '✅',
  turno_rechazado: '🚫',
  recordatorio: '⏰',
  toma_medicacion: '💊', // al paciente: su receta con el plan de toma
  receta_emitida: '📝', // al administrativo: hay una receta para generar el recordatorio
};
const CADA_MS = 60000; // se vuelve a consultar cada minuto

// creada_en llega en UTC sin zona horaria: se le agrega la Z para mostrarla en hora local
function formatear(iso) {
  if (!iso) return '';
  const f = new Date(/[zZ]$|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
  if (Number.isNaN(f.getTime())) return '';
  const dia = f.toLocaleDateString('es-AR', { day: 'numeric', month: 'short' });
  const hora = f.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hour12: false });
  return `${dia} · ${hora} hs`;
}

export default function CampanaNotificaciones() {
  const [items, setItems] = useState([]);
  const [abierto, setAbierto] = useState(false);
  const [error, setError] = useState('');
  const raiz = useRef(null);

  // Consulta inicial y cada minuto. La bandera "activo" evita actualizar el estado si el componente ya se desmontó.
  useEffect(() => {
    let activo = true;
    const traer = async () => {
      try {
        const datos = await api.get('/notificaciones/mias');
        if (!activo) return;
        setItems(datos);
        setError('');
      } catch {
        if (activo) setError('No pudimos cargar tus avisos.');
      }
    };
    traer();
    const intervalo = setInterval(traer, CADA_MS);
    return () => {
      activo = false;
      clearInterval(intervalo);
    };
  }, []);

  // Con el panel abierto: se cierra con Escape o al tocar fuera
  useEffect(() => {
    if (!abierto) return undefined;
    const fuera = (e) => {
      if (raiz.current && !raiz.current.contains(e.target)) setAbierto(false);
    };
    const escape = (e) => {
      if (e.key === 'Escape') setAbierto(false);
    };
    document.addEventListener('mousedown', fuera);
    document.addEventListener('keydown', escape);
    return () => {
      document.removeEventListener('mousedown', fuera);
      document.removeEventListener('keydown', escape);
    };
  }, [abierto]);

  const marcarLeida = async (id) => {
    try {
      const actualizada = await api.patch(`/notificaciones/${id}/leida`);
      setItems((prev) => prev.map((n) => (n.id === id ? actualizada : n)));
    } catch (e) {
      setError(e.message);
    }
  };

  const sinLeer = items.filter((n) => !n.leida).length;

  return (
    <div className="cn" ref={raiz}>
      <button
        type="button"
        className="cn-boton"
        aria-label={sinLeer > 0 ? `Avisos, ${sinLeer} sin leer` : 'Avisos'}
        aria-expanded={abierto}
        onClick={() => setAbierto((a) => !a)}
      >
        <span aria-hidden="true">🔔</span>
        {sinLeer > 0 && <span className="cn-contador" aria-hidden="true">{sinLeer > 9 ? '9+' : sinLeer}</span>}
      </button>

      {abierto && (
        <section className="cn-panel" aria-label="Avisos">
          <h2 className="cn-titulo">Avisos</h2>
          {error && <p className="cn-error" role="alert">{error}</p>}
          {!error && items.length === 0 && <p className="cn-vacio">No tenés avisos por ahora.</p>}
          <ul className="cn-lista">
            {items.map((n) => (
              <li key={n.id} className={`cn-item${n.leida ? '' : ' cn-item--nueva'}`}>
                <span className="cn-icono" aria-hidden="true">{ICONOS[n.tipo] || '🔔'}</span>
                <div className="cn-texto">
                  <p>{n.mensaje}</p>
                  <small>{formatear(n.creada_en)}</small>
                  {!n.leida && (
                    <button type="button" className="cn-leida" onClick={() => marcarLeida(n.id)}>
                      Marcar como leída
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
