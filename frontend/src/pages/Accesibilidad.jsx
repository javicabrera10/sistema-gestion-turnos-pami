import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useAccesibilidad } from '../context/AccesibilidadContext';
import '../styles/paciente.css';
import '../styles/accesibilidad.css';

const INICIO_POR_ROL = {
  paciente: '/paciente',
  medico: '/medico',
  administrativo: '/admin',
};

const TAMANOS = [
  { id: 'normal', etiqueta: 'Normal', clase: 'acc-opcion--normal' },
  { id: 'grande', etiqueta: 'Grande', clase: 'acc-opcion--grande' },
  { id: 'muy_grande', etiqueta: 'Muy grande', clase: 'acc-opcion--muy-grande' },
];

const INTERRUPTORES = [
  { campo: 'alto_contraste', titulo: 'Alto contraste', ayuda: 'Fondo negro, letras blancas y bordes más marcados.' },
  { campo: 'voz_activada', titulo: 'Pedir turnos con la voz', ayuda: 'Muestra la opción de pedir un turno hablando.' },
];

export default function Accesibilidad() {
  const { user, logout } = useAuth();
  const { preferencias, cambiar } = useAccesibilidad();
  const [aviso, setAviso] = useState(null); // { ok, texto }
  const inicio = INICIO_POR_ROL[user?.rol] ?? '/login';

  const actualizar = async (parcial) => {
    setAviso(null);
    try {
      await cambiar(parcial);
      setAviso({ ok: true, texto: 'Listo, guardamos tu elección.' });
    } catch (e) {
      setAviso({ ok: false, texto: e.message });
    }
  };

  return (
    <div className="pac">
      <header className="pac-barra">
        <Link to={inicio} className="pac-marca"><span className="pac-logo" aria-hidden="true" /><strong>PAMI</strong></Link>
        <div className="pac-usuario">
          <span>{user?.nombre || user?.email}</span>
          <button type="button" className="pac-boton pac-boton--claro" onClick={logout}>Salir</button>
        </div>
      </header>

      <main className="pac-contenido">
        <Link to={inicio} className="pac-volver">← Inicio</Link>
        <h1>Accesibilidad</h1>
        <p className="pac-sub">Elegí cómo querés ver la aplicación</p>

        <div className="acc-aviso" aria-live="polite">
          {aviso && <p className={aviso.ok ? 'pac-ok' : 'pac-error'}>{aviso.texto}</p>}
        </div>

        <fieldset className="acc-bloque">
          <legend>Tamaño de letra</legend>
          <div className="acc-opciones">
            {TAMANOS.map((t) => (
              <label key={t.id} className={`acc-opcion ${t.clase}`}>
                <input
                  type="radio"
                  name="tamano_letra"
                  value={t.id}
                  checked={preferencias.tamano_letra === t.id}
                  onChange={() => actualizar({ tamano_letra: t.id })}
                />
                <span>{t.etiqueta}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="acc-bloque">
          <legend>Contraste y voz</legend>
          {INTERRUPTORES.map((i) => (
            <label key={i.campo} className="acc-interruptor">
              <span className="acc-interruptor-texto">
                <strong>{i.titulo}</strong>
                <small>{i.ayuda}</small>
              </span>
              <span className="acc-estado">{preferencias[i.campo] ? 'Activado' : 'Desactivado'}</span>
              <input
                type="checkbox"
                role="switch"
                checked={preferencias[i.campo]}
                onChange={(e) => actualizar({ [i.campo]: e.target.checked })}
              />
            </label>
          ))}
        </fieldset>

        <section className="acc-vista" aria-labelledby="acc-vista-titulo">
          <h2 id="acc-vista-titulo">Vista previa</h2>
          <div className="pac-turno pac-turno--confirmado">
            <div className="pac-turno-fila">
              <p className="acc-muestra-titulo">Cardiología</p>
              <span className="pac-badge pac-badge--confirmado">Confirmado</span>
            </div>
            <p className="pac-fecha">Martes 3 de noviembre · 10:30 hs</p>
            <p className="pac-motivo">Motivo: control de rutina</p>
          </div>
        </section>
      </main>
    </div>
  );
}