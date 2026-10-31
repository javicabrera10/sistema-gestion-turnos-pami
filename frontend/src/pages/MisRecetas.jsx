import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import CampanaNotificaciones from '../components/CampanaNotificaciones';
import '../styles/paciente.css';

function fechaLarga(iso) {
  const f = new Date(iso);
  if (Number.isNaN(f.getTime())) return 'Fecha sin datos';
  const dia = f.toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long' });
  return `${dia.charAt(0).toUpperCase()}${dia.slice(1)}`;
}

const dias = (n) => `${n} ${n === 1 ? 'día' : 'días'}`;

function Receta({ receta }) {
  const esOrden = receta.tipo === 'orden';
  const medicamentos = receta.medicamentos || [];
  const plan = receta.plan_medicacion || [];

  return (
    <li className="pac-turno pac-turno--confirmado">
      <div className="pac-turno-fila">
        <h2>{esOrden ? 'Pedido de estudios' : 'Receta'}</h2>
        <span className="pac-badge pac-badge--confirmado">{esOrden ? 'Orden' : 'Receta'}</span>
      </div>
      <p className="pac-fecha">Emitida: {fechaLarga(receta.fecha)}</p>

      {!esOrden && medicamentos.length > 0 && (
        <>
          <h3 className="pac-receta-titulo">Medicamentos</h3>
          <ul className="pac-receta-items">
            {medicamentos.map((m) => (
              <li key={`${m.nombre}-${m.dosis}`}>
                <strong>{m.nombre}</strong> · {m.dosis}
                {m.presentacion ? ` · ${m.presentacion}` : ''}
                {m.horario_toma ? ` · ${m.horario_toma}` : ''}
              </li>
            ))}
          </ul>
        </>
      )}

      {plan.length > 0 && (
        <>
          <h3 className="pac-receta-titulo">Cuándo tomarlos</h3>
          <ul className="pac-receta-items">
            {plan.map((p) => (
              <li key={`${p.medicamento}-${p.horarios.join()}`}>
                <strong>{p.medicamento}</strong> ({p.dosis}) a las {p.horarios.join(', ')} hs durante {dias(p.duracion_dias)}
              </li>
            ))}
          </ul>
        </>
      )}

      {receta.indicaciones && (
        <p className="pac-motivo">
          {esOrden ? 'Qué tenés que hacerte: ' : 'Indicaciones: '}
          {receta.indicaciones}
        </p>
      )}
    </li>
  );
}

export default function MisRecetas() {
  const { user, logout } = useAuth();
  const [recetas, setRecetas] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let activo = true;
    const cargar = async () => {
      try {
        const datos = await api.get('/recetas/mias');
        if (activo) setRecetas(datos);
      } catch (e) {
        if (activo) setError(e.message);
      } finally {
        if (activo) setCargando(false);
      }
    };
    cargar();
    return () => { activo = false; };
  }, []);

  return (
    <div className="pac">
      <header className="pac-barra">
        <Link to="/paciente" className="pac-marca"><span className="pac-logo" aria-hidden="true" /><strong>PAMI</strong></Link>
        <div className="pac-usuario">
          <CampanaNotificaciones />
          <span>{user?.nombre || user?.email}</span>
          <button type="button" className="pac-boton pac-boton--claro" onClick={logout}>Salir</button>
        </div>
      </header>

      <main className="pac-contenido">
        <Link to="/paciente" className="pac-volver">← Inicio</Link>
        <h1>Mis recetas y estudios</h1>
        {error && <p className="pac-error" role="alert">{error}</p>}
        {cargando && <p>Cargando tus recetas…</p>}

        {!cargando && !error && recetas.length === 0 && (
          <div className="pac-vacio">
            <p>Todavía no tenés recetas ni pedidos de estudios.</p>
          </div>
        )}

        <ul className="pac-lista" aria-label="Recetas y pedidos de estudios">
          {recetas.map((r) => <Receta key={r.id} receta={r} />)}
        </ul>
      </main>
    </div>
  );
}
