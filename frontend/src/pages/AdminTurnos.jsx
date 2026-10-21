import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import '../styles/admin.css';

const FILTROS = [
  { id: 'todos', label: 'Todos' },
  { id: 'solicitado', label: 'Pendientes' },
  { id: 'otorgado', label: 'Otorgados' },
  { id: 'confirmado', label: 'Confirmados' },
  { id: 'rechazado', label: 'Rechazados' },
];

const RESUMEN = [
  { id: 'solicitado', label: 'Pendientes', ayuda: 'esperan que los otorgues' },
  { id: 'otorgado', label: 'Otorgados', ayuda: 'esperan respuesta del paciente' },
  { id: 'confirmado', label: 'Confirmados', ayuda: 'el paciente aceptó' },
  { id: 'rechazado', label: 'Rechazados', ayuda: 'el paciente rechazó' },
];

const ETIQUETA = {
  solicitado: 'Pendiente',
  otorgado: 'Otorgado',
  confirmado: 'Confirmado',
  rechazado: 'Rechazado',
  reprogramado: 'Reprogramado',
  cancelado: 'Cancelado',
};

const quitarTildes = (s) => (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
const dos = (n) => String(n).padStart(2, '0');

function formatearFecha(iso) {
  if (!iso) return 'Sin fecha';
  const f = new Date(iso);
  if (Number.isNaN(f.getTime())) return 'Sin fecha';
  const dia = f.toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric', month: 'short' });
  return `${dia} · ${dos(f.getHours())}:${dos(f.getMinutes())} hs`;
}

function iniciales(nombre) {
  return (nombre || '?')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0].toUpperCase())
    .join('');
}

function PanelOtorgar({ turno, medicos, onListo, onCancelar }) {
  const pedido = new Date(turno.fecha_hora);
  const valido = !Number.isNaN(pedido.getTime());
  const sugerido = medicos.find((m) => quitarTildes(m.especialidad) === quitarTildes(turno.especialidad));

  const [medicoId, setMedicoId] = useState(sugerido?.id || '');
  const [fecha, setFecha] = useState(valido ? `${pedido.getFullYear()}-${dos(pedido.getMonth() + 1)}-${dos(pedido.getDate())}` : '');
  const [hora, setHora] = useState(valido ? `${dos(pedido.getHours())}:${dos(pedido.getMinutes())}` : '');
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);

  const enviar = async (e) => {
    e.preventDefault();
    setEnviando(true);
    setError('');
    try {
      await api.patch(`/turnos/${turno.id}/otorgar`, { medico_id: medicoId, fecha_hora: `${fecha}T${hora}:00` });
      onListo();
    } catch (err) {
      setError(err.message);
      setEnviando(false);
    }
  };

  return (
    <form className="adm-otorgar" onSubmit={enviar}>
      <p className="adm-otorgar-titulo">Confirmá médico, día y hora</p>
      <div className="adm-otorgar-campos">
        <label>
          Médico
          <select value={medicoId} onChange={(e) => setMedicoId(e.target.value)} required>
            <option value="">Elegí un médico…</option>
            {medicos.map((m) => (
              <option key={m.id} value={m.id}>
                {m.nombre}{m.especialidad ? ` · ${m.especialidad}` : ''}
              </option>
            ))}
          </select>
        </label>
        <label>
          Día
          <input type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} required />
        </label>
        <label>
          Hora
          <input type="time" value={hora} onChange={(e) => setHora(e.target.value)} required />
        </label>
      </div>
      {medicos.length === 0 && <p className="adm-aviso">No hay médicos cargados todavía.</p>}
      {error && <p className="adm-error" role="alert">{error}</p>}
      <div className="adm-otorgar-botones">
        <button type="submit" className="adm-boton adm-boton--primario" disabled={enviando}>
          {enviando ? 'Otorgando…' : 'Otorgar turno'}
        </button>
        <button type="button" className="adm-boton" onClick={onCancelar}>Cancelar</button>
      </div>
    </form>
  );
}

export default function AdminTurnos() {
  const { user, logout } = useAuth();
  const [turnos, setTurnos] = useState([]);
  const [medicos, setMedicos] = useState([]);
  const [filtro, setFiltro] = useState('solicitado');
  const [abierto, setAbierto] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');
  const [exito, setExito] = useState('');

  const cargar = useCallback(async () => {
    setCargando(true);
    setError('');
    try {
      const [ts, us] = await Promise.all([api.get('/turnos'), api.get('/usuarios').catch(() => [])]);
      setTurnos(ts);
      setMedicos(us.filter((u) => u.rol === 'medico'));
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    cargar();
  }, [cargar]);

  const cuenta = useMemo(() => {
    const c = {};
    turnos.forEach((t) => { c[t.estado] = (c[t.estado] || 0) + 1; });
    return c;
  }, [turnos]);

  const visibles = turnos.filter((t) => filtro === 'todos' || t.estado === filtro);
  const nombreMedico = (id) => medicos.find((m) => m.id === id)?.nombre;

  const alOtorgar = () => {
    setAbierto(null);
    setExito('Turno otorgado. El paciente ya puede verlo.');
    cargar();
  };

  return (
    <div className="adm">
      <header className="adm-barra">
        <div className="adm-marca">
          <span className="adm-logo" aria-hidden="true" />
          <div>
            <strong>PAMI</strong>
            <span>Panel administrativo</span>
          </div>
        </div>
        <div className="adm-usuario">
          <span>{user?.nombre || user?.email}</span>
          <button type="button" className="adm-boton" onClick={logout}>Salir</button>
        </div>
      </header>

      <main className="adm-contenido">
        <h1>Solicitudes de turnos</h1>
        <p className="adm-sub">Revisá los pedidos de los pacientes y otorgá fecha, hora y médico.</p>

        <section className="adm-resumen" aria-label="Resumen por estado">
          {RESUMEN.map((r) => (
            <button
              key={r.id}
              type="button"
              className={`adm-tarjeta adm-tarjeta--${r.id}${filtro === r.id ? ' adm-tarjeta--activa' : ''}`}
              onClick={() => setFiltro(r.id)}
            >
              <span className="adm-numero">{cuenta[r.id] || 0}</span>
              <span className="adm-tarjeta-label">{r.label}</span>
              <span className="adm-tarjeta-ayuda">{r.ayuda}</span>
            </button>
          ))}
        </section>

        <div className="adm-filtros" role="tablist" aria-label="Filtrar por estado">
          {FILTROS.map((f) => (
            <button
              key={f.id}
              type="button"
              role="tab"
              aria-selected={filtro === f.id}
              className={`adm-filtro${filtro === f.id ? ' adm-filtro--activo' : ''}`}
              onClick={() => setFiltro(f.id)}
            >
              {f.label}
            </button>
          ))}
          <button type="button" className="adm-boton adm-actualizar" onClick={cargar} disabled={cargando}>
            ↻ Actualizar
          </button>
        </div>

        {exito && <p className="adm-exito" role="status">{exito}</p>}
        {error && <p className="adm-error" role="alert">{error}</p>}
        {cargando && <p className="adm-aviso">Cargando solicitudes…</p>}
        {!cargando && !error && visibles.length === 0 && (
          <div className="adm-vacio">
            <span aria-hidden="true">📭</span>
            <p>No hay turnos en esta categoría.</p>
          </div>
        )}

        <ul className="adm-lista">
          {visibles.map((t) => (
            <li key={t.id} className="adm-turno">
              <div className="adm-turno-cabecera">
                <span className="adm-avatar" aria-hidden="true">{iniciales(t.paciente?.nombre)}</span>
                <div className="adm-turno-paciente">
                  <strong>{t.paciente?.nombre || 'Paciente'}</strong>
                  <span>
                    {t.paciente?.dni ? `DNI ${t.paciente.dni}` : 'Sin DNI'}
                    {t.paciente?.telefono ? ` · Tel. ${t.paciente.telefono}` : ''}
                  </span>
                </div>
                <span className={`adm-badge adm-badge--${t.estado}`}>{ETIQUETA[t.estado] || t.estado}</span>
              </div>

              <dl className="adm-datos">
                <div><dt>Especialidad</dt><dd>{t.especialidad}</dd></div>
                <div><dt>{t.estado === 'solicitado' ? 'Fecha pedida' : 'Fecha del turno'}</dt><dd>{formatearFecha(t.fecha_hora)}</dd></div>
                <div><dt>Médico</dt><dd>{nombreMedico(t.medico_id) || (t.medico_id ? 'Asignado' : 'Sin asignar')}</dd></div>
                <div className="adm-dato-ancho"><dt>Motivo</dt><dd>{t.motivo}</dd></div>
              </dl>

              {t.estado === 'solicitado' && abierto !== t.id && (
                <button type="button" className="adm-boton adm-boton--primario" onClick={() => { setAbierto(t.id); setExito(''); }}>
                  Otorgar turno
                </button>
              )}
              {abierto === t.id && (
                <PanelOtorgar turno={t} medicos={medicos} onListo={alOtorgar} onCancelar={() => setAbierto(null)} />
              )}
            </li>
          ))}
        </ul>
      </main>
    </div>
  );
}
