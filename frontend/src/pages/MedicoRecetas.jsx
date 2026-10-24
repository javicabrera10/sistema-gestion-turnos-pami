import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import '../styles/receta.css';

// El backend acepta /api/recetas con y sin barra final (strict_slashes=False), así que no hay 308.
const RUTA_RECETAS = '/recetas';

const MED_VACIO = { nombre: '', dosis: '', horario_toma: '' };

export default function MedicoRecetas() {
  const { user, logout } = useAuth();
  const [tipo, setTipo] = useState('receta'); // 'receta' | 'orden'

  // Paciente: se busca por DNI; si el backend no tiene la búsqueda, se carga el ID a mano
  const [dni, setDni] = useState('');
  const [paciente, setPaciente] = useState(null); // { id, nombre, dni }
  const [busqueda, setBusqueda] = useState({ estado: 'idle', texto: '' });
  const [pacienteIdManual, setPacienteIdManual] = useState('');
  const [modoManual, setModoManual] = useState(false);

  const [medicamentos, setMedicamentos] = useState([{ ...MED_VACIO }]);
  const [indicaciones, setIndicaciones] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState(null); // { ok, texto }
  const [historial, setHistorial] = useState([]); // lo creado en esta sesión

  const pacienteId = paciente?.id || pacienteIdManual.trim();

  const buscarPaciente = async () => {
    setPaciente(null);
    if (!/^\d{7,8}$/.test(dni.trim())) {
      setBusqueda({ estado: 'error', texto: 'El DNI tiene 7 u 8 números, sin puntos.' });
      return;
    }
    setBusqueda({ estado: 'buscando', texto: '' });
    try {
      const lista = await api.get(`/pacientes?dni=${dni.trim()}`);
      if (lista.length === 0) setBusqueda({ estado: 'error', texto: 'No encontramos un paciente con ese DNI.' });
      else {
        setPaciente(lista[0]);
        setBusqueda({ estado: 'ok', texto: '' });
      }
    } catch {
      setModoManual(true);
      setBusqueda({ estado: 'error', texto: 'La búsqueda por DNI todavía no está disponible. Cargá el ID del paciente.' });
    }
  };

  const cambiarMed = (i, campo, valor) =>
    setMedicamentos((prev) => prev.map((m, j) => (j === i ? { ...m, [campo]: valor } : m)));

  const limpiar = () => {
    setMedicamentos([{ ...MED_VACIO }]);
    setIndicaciones('');
    setDni('');
    setPaciente(null);
    setPacienteIdManual('');
    setBusqueda({ estado: 'idle', texto: '' });
  };

  const guardar = async (emitir) => {
    setResultado(null);
    if (!pacienteId) return setResultado({ ok: false, texto: 'Elegí un paciente primero.' });
    if (tipo === 'receta' && medicamentos.some((m) => !m.nombre.trim() || !m.dosis.trim() || !m.horario_toma.trim())) {
      return setResultado({ ok: false, texto: 'Completá nombre, dosis y horario de cada medicamento.' });
    }
    if (tipo === 'orden' && indicaciones.trim().length < 3) {
      return setResultado({ ok: false, texto: 'Escribí qué estudio o práctica indicás.' });
    }

    setEnviando(true);
    try {
      // tipo: 'receta' lleva medicamentos; 'orden' (estudio o práctica) lleva todo en las indicaciones.
      const creada = await api.post(RUTA_RECETAS, {
        paciente_id: pacienteId,
        tipo,
        indicaciones: indicaciones.trim(),
        medicamentos: tipo === 'receta' ? medicamentos.map((m) => ({ nombre: m.nombre.trim(), dosis: m.dosis.trim(), horario_toma: m.horario_toma.trim() })) : [],
      });
      if (emitir) await api.post(`/recetas/${creada.id}/emitir`);
      const nombre = paciente?.nombre || `paciente ${pacienteId}`;
      setHistorial((h) => [{ id: creada.id, tipo, nombre, emitida: emitir }, ...h]);
      setResultado({ ok: true, texto: `${tipo === 'receta' ? 'Receta' : 'Orden'} ${emitir ? 'emitida al paciente' : 'guardada como borrador'}.` });
      limpiar();
    } catch (e) {
      setResultado({ ok: false, texto: e.message });
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="rec">
      <header className="rec-barra">
        <div className="rec-marca"><span className="rec-logo" aria-hidden="true" /><div><strong>PAMI</strong><span>Panel médico</span></div></div>
        <div className="rec-usuario">
          <span>{user?.nombre || user?.email}</span>
          <button type="button" className="rec-boton rec-boton--claro" onClick={logout}>Salir</button>
        </div>
      </header>

      <main className="rec-contenido">
        <h1>Recetas y órdenes digitales</h1>
        <p className="rec-sub">Generá el documento y emitilo al paciente.</p>

        <div className="rec-tipos" role="tablist" aria-label="Tipo de documento">
          {[['receta', '💊 Receta'], ['orden', '📋 Orden (estudio o práctica)']].map(([id, label]) => (
            <button key={id} type="button" role="tab" aria-selected={tipo === id} className={`rec-tipo${tipo === id ? ' rec-tipo--activo' : ''}`} onClick={() => setTipo(id)}>
              {label}
            </button>
          ))}
        </div>

        <form className="rec-form" onSubmit={(e) => e.preventDefault()}>
          <fieldset className="rec-bloque">
            <legend>1. Paciente</legend>
            {!modoManual ? (
              <div className="rec-buscar">
                <label>
                  DNI del paciente
                  <input inputMode="numeric" maxLength={8} placeholder="Ej. 12345678" value={dni} onChange={(e) => setDni(e.target.value.replace(/\D/g, ''))} />
                </label>
                <button type="button" className="rec-boton" onClick={buscarPaciente} disabled={busqueda.estado === 'buscando'}>
                  {busqueda.estado === 'buscando' ? 'Buscando…' : 'Buscar'}
                </button>
              </div>
            ) : (
              <label>
                ID del paciente
                <input value={pacienteIdManual} onChange={(e) => setPacienteIdManual(e.target.value)} placeholder="Pegá el ID del paciente" />
              </label>
            )}
            {paciente && <p className="rec-paciente">✔ {paciente.nombre} · DNI {paciente.dni}</p>}
            {busqueda.estado === 'error' && <p className="rec-aviso">{busqueda.texto}</p>}
          </fieldset>

          {tipo === 'receta' ? (
            <fieldset className="rec-bloque">
              <legend>2. Medicamentos</legend>
              {medicamentos.map((m, i) => (
                <div key={i} className="rec-med">
                  <div className="rec-med-cab">
                    <strong>Medicamento {i + 1}</strong>
                    {medicamentos.length > 1 && (
                      <button type="button" className="rec-quitar" onClick={() => setMedicamentos((p) => p.filter((_, j) => j !== i))} aria-label={`Quitar medicamento ${i + 1}`}>Quitar</button>
                    )}
                  </div>
                  <div className="rec-med-campos">
                    <label>Nombre<input value={m.nombre} onChange={(e) => cambiarMed(i, 'nombre', e.target.value)} placeholder="Ej. Ibuprofeno" /></label>
                    <label>Dosis<input value={m.dosis} onChange={(e) => cambiarMed(i, 'dosis', e.target.value)} placeholder="Ej. 400 mg" /></label>
                    <label>Horario<input value={m.horario_toma} onChange={(e) => cambiarMed(i, 'horario_toma', e.target.value)} placeholder="Ej. Cada 8 horas" /></label>
                  </div>
                </div>
              ))}
              <button type="button" className="rec-boton" onClick={() => setMedicamentos((p) => [...p, { ...MED_VACIO }])}>+ Agregar otro medicamento</button>
            </fieldset>
          ) : null}

          <fieldset className="rec-bloque">
            <legend>{tipo === 'receta' ? '3. Indicaciones (opcional)' : '2. Estudio o práctica indicada'}</legend>
            <textarea
              rows={4}
              value={indicaciones}
              onChange={(e) => setIndicaciones(e.target.value)}
              placeholder={tipo === 'receta' ? 'Ej. Tomar después de las comidas.' : 'Ej. Radiografía de rodilla izquierda, frente y perfil.'}
            />
          </fieldset>

          {resultado && <p className={resultado.ok ? 'rec-ok' : 'rec-error'} role={resultado.ok ? 'status' : 'alert'}>{resultado.texto}</p>}

          <div className="rec-acciones">
            <button type="button" className="rec-boton rec-boton--primario" disabled={enviando} onClick={() => guardar(true)}>
              {enviando ? 'Enviando…' : `Emitir ${tipo} al paciente`}
            </button>
            <button type="button" className="rec-boton" disabled={enviando} onClick={() => guardar(false)}>Guardar borrador</button>
          </div>
        </form>

        {historial.length > 0 && (
          <section className="rec-historial" aria-labelledby="rec-hist">
            <h2 id="rec-hist">Creadas en esta sesión</h2>
            <ul>
              {historial.map((h) => (
                <li key={h.id}>
                  <span>{h.tipo === 'receta' ? '💊' : '📋'} {h.nombre}</span>
                  <span className={`rec-estado rec-estado--${h.emitida ? 'emitida' : 'borrador'}`}>{h.emitida ? 'Emitida' : 'Borrador'}</span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </main>
    </div>
  );
}
