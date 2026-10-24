import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import '../styles/paciente.css';

const ETIQUETA = {
  solicitado: 'Esperando que te den fecha',
  otorgado: 'Tenés que responder',
  confirmado: 'Confirmado',
  rechazado: 'Rechazado',
  reprogramado: 'Reprogramado',
  cancelado: 'Cancelado',
};
const ORDEN = { otorgado: 0, confirmado: 1, solicitado: 2, reprogramado: 3, rechazado: 4, cancelado: 5 };

function fechaLarga(iso) {
  const f = new Date(iso);
  if (Number.isNaN(f.getTime())) return 'Fecha a confirmar';
  const dia = f.toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });
  const hora = f.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hour12: false });
  return `${dia.charAt(0).toUpperCase()}${dia.slice(1)} · ${hora} hs`;
}

export default function MisTurnos() {
  const { user, logout } = useAuth();
  const [turnos, setTurnos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [rechazando, setRechazando] = useState(null); // id del turno que pide confirmación
  const [enviando, setEnviando] = useState(null);

  // Recarga manual (después de responder un turno): muestra el cargando y limpia el error.
  const cargar = useCallback(async () => {
    setCargando(true);
    setError('');
    try {
      setTurnos(await api.get('/turnos/mios'));
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }, []);

  // Carga inicial: el estado arranca en cargando=true y error='', así que no hace falta setearlos acá.
  useEffect(() => {
    let activo = true;
    const cargarInicial = async () => {
      try {
        const datos = await api.get('/turnos/mios');
        if (activo) setTurnos(datos);
      } catch (e) {
        if (activo) setError(e.message);
      } finally {
        if (activo) setCargando(false);
      }
    };
    cargarInicial();
    return () => { activo = false; };
  }, []);

  const responder = async (turno, accion) => {
    setEnviando(turno.id);
    setError('');
    setMensaje('');
    try {
      await api.patch(`/turnos/${turno.id}/${accion === 'aceptar' ? 'confirmar' : 'rechazar'}`);
      setMensaje(accion === 'aceptar' ? '¡Listo! Confirmaste tu turno.' : 'Rechazaste el turno.');
      setRechazando(null);
      await cargar();
    } catch (e) {
      setError(e.message);
    } finally {
      setEnviando(null);
    }
  };

  const ordenados = [...turnos].sort((a, b) => (ORDEN[a.estado] ?? 9) - (ORDEN[b.estado] ?? 9));
  const porResponder = turnos.filter((t) => t.estado === 'otorgado').length;

  return (
    <div className="pac">
      <header className="pac-barra">
        <Link to="/paciente" className="pac-marca"><span className="pac-logo" aria-hidden="true" /><strong>PAMI</strong></Link>
        <div className="pac-usuario">
          <span>{user?.nombre || user?.email}</span>
          <button type="button" className="pac-boton pac-boton--claro" onClick={logout}>Salir</button>
        </div>
      </header>

      <main className="pac-contenido">
        <Link to="/paciente" className="pac-volver">← Inicio</Link>
        <h1>Mis turnos</h1>
        {porResponder > 0 && (
          <p className="pac-aviso" role="status">
            Tenés {porResponder} {porResponder === 1 ? 'turno' : 'turnos'} para aceptar o rechazar.
          </p>
        )}
        {mensaje && <p className="pac-ok" role="status">{mensaje}</p>}
        {error && <p className="pac-error" role="alert">{error}</p>}
        {cargando && <p>Cargando tus turnos…</p>}

        {!cargando && !error && turnos.length === 0 && (
          <div className="pac-vacio">
            <p>Todavía no pediste ningún turno.</p>
            <Link to="/paciente/turnos/nuevo" className="pac-boton pac-boton--primario">Pedir un turno</Link>
          </div>
        )}

        <ul className="pac-lista">
          {ordenados.map((t) => (
            <li key={t.id} className={`pac-turno pac-turno--${t.estado}`}>
              <div className="pac-turno-fila">
                <h2>{t.especialidad}</h2>
                <span className={`pac-badge pac-badge--${t.estado}`}>{ETIQUETA[t.estado] || t.estado}</span>
              </div>
              <p className="pac-fecha">
                {t.estado === 'solicitado' ? 'Fecha que pediste: ' : ''}
                {fechaLarga(t.fecha_hora)}
              </p>
              <p className="pac-motivo">Motivo: {t.motivo}</p>

              {t.estado === 'otorgado' && rechazando !== t.id && (
                <div className="pac-acciones">
                  <button type="button" className="pac-boton pac-boton--aceptar" disabled={enviando === t.id} onClick={() => responder(t, 'aceptar')}>
                    ✔ Aceptar turno
                  </button>
                  <button type="button" className="pac-boton pac-boton--rechazar" disabled={enviando === t.id} onClick={() => setRechazando(t.id)}>
                    ✖ Rechazar
                  </button>
                </div>
              )}
              {rechazando === t.id && (
                <div className="pac-confirmar" role="alertdialog" aria-label="Confirmar rechazo">
                  <p>¿Seguro que querés rechazar este turno?</p>
                  <div className="pac-acciones">
                    <button type="button" className="pac-boton pac-boton--rechazar" disabled={enviando === t.id} onClick={() => responder(t, 'rechazar')}>
                      Sí, rechazar
                    </button>
                    <button type="button" className="pac-boton" onClick={() => setRechazando(null)}>No, volver</button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      </main>
    </div>
  );
}
