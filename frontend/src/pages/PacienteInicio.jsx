import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import CampanaNotificaciones from '../components/CampanaNotificaciones';
import '../styles/paciente.css';

export default function PacienteInicio() {
  const { user, logout } = useAuth();
  const [porResponder, setPorResponder] = useState(0);

  useEffect(() => {
    api.get('/turnos/mios')
      .then((ts) => setPorResponder(ts.filter((t) => t.estado === 'otorgado' || t.estado === 'reprogramado').length))
      .catch(() => {}); // si falla, simplemente no mostramos el aviso
  }, []);

  return (
    <div className="pac">
      <header className="pac-barra">
        <div className="pac-marca"><span className="pac-logo" aria-hidden="true" /><strong>PAMI</strong></div>
        <div className="pac-usuario">
          <CampanaNotificaciones />
          <span>{user?.nombre || user?.email}</span>
          <button type="button" className="pac-boton pac-boton--claro" onClick={logout}>Salir</button>
        </div>
      </header>

      <main className="pac-contenido">
        <h1>Hola{user?.nombre ? `, ${user.nombre.split(' ')[0]}` : ''} 👋</h1>
        <p className="pac-sub">¿Qué necesitás hacer hoy?</p>

        {porResponder > 0 && (
          <Link to="/paciente/turnos" className="pac-alerta-turno">
            🔔 Tenés {porResponder} {porResponder === 1 ? 'turno' : 'turnos'} para aceptar o rechazar. <strong>Verlo ahora →</strong>
          </Link>
        )}

        <nav className="pac-menu" aria-label="Opciones principales">
          <Link to="/paciente/turnos/nuevo" className="pac-opcion">
            <span className="pac-icono" aria-hidden="true">📅</span>
            <span><strong>Pedir un turno</strong><small>Podés escribirlo o decirlo con la voz</small></span>
          </Link>
          <Link to="/paciente/turnos" className="pac-opcion">
            <span className="pac-icono" aria-hidden="true">🩺</span>
            <span><strong>Mis turnos</strong><small>Mirá tus turnos y respondé si los aceptás</small></span>
          </Link>
          <Link to="/paciente/familiar" className="pac-opcion">
            <span className="pac-icono" aria-hidden="true">👪</span>
            <span><strong>Mi familiar autorizado</strong><small>Elegí a quién avisarle de tus turnos</small></span>
          </Link>
          <Link to="/accesibilidad" className="pac-opcion">
            <span className="pac-icono" aria-hidden="true">&#9881;&#65039;</span>
            <span><strong>Accesibilidad</strong><small>Elegí el tamaño de letra, el contraste y la voz</small></span>
          </Link>
        </nav>
      </main>
    </div>
  );
}
