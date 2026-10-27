import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import '../styles/receta.css';

// El backend acepta /api/recetas con y sin barra final (strict_slashes=False), así que no hay 308.
const RUTA_RECETAS = '/recetas';

const MED_VACIO = { nombre: '', dosis: '', horario_toma: '', horarios: [], duracion_dias: '' };
const HORA = /^([01]\d|2[0-3]):[0-5]\d$/;
const MAX_HORARIOS = 12; // el backend no acepta más por medicamento

// Plan de medicación: solo entran los medicamentos que tienen horarios (el aviso de toma es opcional)
function armarPlan(medicamentos) {
  return medicamentos
    .filter((m) => m.horarios.length > 0)
    .map((m) => ({
      medicamento: m.nombre.trim(),
      dosis: m.dosis.trim(),
      horarios: [...m.horarios].sort(),
      duracion_dias: Number(m.duracion_dias),
    }));
}

// Mismas reglas que el backend, para explicar el problema antes de enviar. El backend siempre valida de nuevo.
function problemaDelPlan(medicamentos) {
  for (const m of medicamentos) {
    const nombre = m.nombre.trim() || 'el medicamento';
    const conHorarios = m.horarios.length > 0;
    const conDuracion = String(m.duracion_dias).trim() !== '';
    if (!conHorarios && !conDuracion) continue;
    if (m.horarios.some((h) => !HORA.test(h))) return `Completá todos los horarios de ${nombre}.`;
    if (!conHorarios || !conDuracion) return `Para el aviso de toma de ${nombre} cargá los horarios y la duración, o dejá los dos vacíos.`;
    const dias = Number(m.duracion_dias);
    if (!Number.isInteger(dias) || dias < 1 || dias > 365) return `La duración de ${nombre} tiene que ser de 1 a 365 días.`;
    if (new Set(m.horarios).size !== m.horarios.length) return `Hay horarios repetidos en ${nombre}.`;
  }
  return '';
}

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

  const cambiarMedicamento = (i, cambio) =>
    setMedicamentos((prev) => prev.map((m, j) => (j === i ? { ...m, ...cambio(m) } : m)));
  const agregarHorario = (i) => cambiarMedicamento(i, (m) => ({ horarios: [...m.horarios, ''] }));
  const cambiarHorario = (i, k, valor) => cambiarMedicamento(i, (m) => ({ horarios: m.horarios.map((h, n) => (n === k ? valor : h)) }));
  const quitarHorario = (i, k) => cambiarMedicamento(i, (m) => ({ horarios: m.horarios.filter((_, n) => n !== k) }));

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
    if (tipo === 'receta') {
      const problema = problemaDelPlan(medicamentos);
      if (problema) return setResultado({ ok: false, texto: problema });
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
      const nombre = paciente?.nombre || `paciente ${pacienteId}`;
      const plan = tipo === 'receta' ? armarPlan(medicamentos) : [];
      // El plan se carga antes de emitir: el tratamiento empieza a contar cuando la receta se emite
      if (plan.length > 0) {
        try {
          await api.put(`/recetas/${creada.id}/plan`, { plan });
        } catch (e) {
          setHistorial((h) => [{ id: creada.id, tipo, nombre, emitida: false, conPlan: false }, ...h]);
          setResultado({ ok: false, texto: `La receta quedó guardada como borrador, pero no se pudo cargar el plan de toma: ${e.message}` });
          limpiar();
          return;
        }
      }
      if (emitir) await api.post(`/recetas/${creada.id}/emitir`);
      setHistorial((h) => [{ id: creada.id, tipo, nombre, emitida: emitir, conPlan: plan.length > 0 }, ...h]);
      const avisoToma = plan.length > 0 && emitir ? ' El paciente va a recibir un aviso a cada horario de toma.' : '';
      setResultado({ ok: true, texto: `${tipo === 'receta' ? 'Receta' : 'Orden'} ${emitir ? 'emitida al paciente' : 'guardada como borrador'}.${avisoToma}` });
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
                  <div className="rec-plan">
                    <p className="rec-plan-titulo">Aviso de toma al paciente <span>(opcional)</span></p>
                    <p className="rec-plan-ayuda">Si cargás los horarios y los días, el paciente recibe un aviso a cada hora, desde que emitís la receta.</p>
                    <div className="rec-plan-campos">
                      <label>
                        Duración (días)
                        <input type="number" min="1" max="365" inputMode="numeric" value={m.duracion_dias} onChange={(e) => cambiarMed(i, 'duracion_dias', e.target.value)} placeholder="Ej. 7" />
                      </label>
                      <div className="rec-horarios">
                        <span className="rec-horarios-titulo">Horarios de toma</span>
                        {m.horarios.map((h, k) => (
                          <div key={k} className="rec-horario">
                            <input type="time" value={h} onChange={(e) => cambiarHorario(i, k, e.target.value)} aria-label={`Horario ${k + 1} del medicamento ${i + 1}`} />
                            <button type="button" className="rec-quitar" onClick={() => quitarHorario(i, k)} aria-label={`Quitar horario ${k + 1} del medicamento ${i + 1}`}>Quitar</button>
                          </div>
                        ))}
                        <button type="button" className="rec-boton" onClick={() => agregarHorario(i)} disabled={m.horarios.length >= MAX_HORARIOS}>+ Agregar horario</button>
                      </div>
                    </div>
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
                  <span>{h.tipo === 'receta' ? '💊' : '📋'} {h.nombre}{h.conPlan ? ' · con aviso de toma' : ''}</span>
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
