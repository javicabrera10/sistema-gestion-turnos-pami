import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import CampanaNotificaciones from '../components/CampanaNotificaciones';
import '../styles/paciente.css';
import '../styles/familiar.css';

const VACIO = { nombre: '', parentesco: '', canal: 'sms', contacto: '' };
const CANALES = { sms: 'SMS', email: 'Email' };

function desdeFamiliar(f) {
  return { nombre: f.nombre, parentesco: f.parentesco, canal: f.canal, contacto: f.contacto };
}

// Las mismas reglas que el backend, para explicar el error antes de enviar. El backend siempre valida de nuevo.
function validar(form, consentimiento) {
  if (form.nombre.trim().length < 2) return 'Escribí el nombre del familiar.';
  if (form.parentesco.trim().length < 2) return 'Escribí qué parentesco tiene (por ejemplo: hija, hermano).';
  if (form.canal === 'email') {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.contacto.trim())) return 'El email del familiar no es válido.';
  } else if (!/^\+?\d{8,15}$/.test(form.contacto.replace(/[\s\-().]/g, ''))) {
    return 'El teléfono del familiar no es válido (solo números, de 8 a 15 dígitos).';
  }
  if (!consentimiento) return 'Para guardar tenés que marcar que autorizás el aviso.';
  return '';
}

// creado_en llega en UTC sin zona horaria: se le agrega la Z para mostrarla en hora local
function fechaLocal(iso) {
  if (!iso) return '';
  const f = new Date(/[zZ]$|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
  if (Number.isNaN(f.getTime())) return '';
  const dia = f.toLocaleDateString('es-AR', { day: 'numeric', month: 'short' });
  const hora = f.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit', hour12: false });
  return `${dia} · ${hora} hs`;
}

export default function PacienteFamiliar() {
  const { user, logout } = useAuth();
  const [cargando, setCargando] = useState(true);
  const [familiar, setFamiliar] = useState(null);
  const [avisos, setAvisos] = useState([]);
  const [form, setForm] = useState(VACIO);
  const [consentimiento, setConsentimiento] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [quitando, setQuitando] = useState(false); // mostrando la confirmación para quitar
  const [mensaje, setMensaje] = useState('');
  const [error, setError] = useState('');

  // Carga inicial. La bandera "activo" evita actualizar el estado si la pantalla ya se cerró.
  useEffect(() => {
    let activo = true;
    const cargar = async () => {
      try {
        const [actual, enviados] = await Promise.all([api.get('/familiar'), api.get('/familiar/avisos')]);
        if (!activo) return;
        setFamiliar(actual.familiar);
        setAvisos(enviados);
        if (actual.familiar) setForm(desdeFamiliar(actual.familiar));
      } catch (e) {
        if (activo) setError(e.message);
      } finally {
        if (activo) setCargando(false);
      }
    };
    cargar();
    return () => {
      activo = false;
    };
  }, []);

  const cambiar = (campo, valor) => setForm((f) => ({ ...f, [campo]: valor }));

  const guardar = async (e) => {
    e.preventDefault();
    setMensaje('');
    const problema = validar(form, consentimiento);
    if (problema) {
      setError(problema);
      return;
    }
    setError('');
    setGuardando(true);
    try {
      const { familiar: guardado } = await api.put('/familiar', {
        nombre: form.nombre.trim(),
        parentesco: form.parentesco.trim(),
        canal: form.canal,
        contacto: form.contacto.trim(),
        consentimiento: true,
      });
      setFamiliar(guardado);
      setForm(desdeFamiliar(guardado));
      setConsentimiento(false); // para cada cambio se vuelve a pedir la autorización
      setMensaje(`Listo: a partir de ahora le avisamos a ${guardado.nombre} de tus turnos.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setGuardando(false);
    }
  };

  const quitar = async () => {
    setError('');
    setMensaje('');
    setGuardando(true);
    try {
      await api.delete('/familiar');
      setFamiliar(null);
      setForm(VACIO);
      setConsentimiento(false);
      setQuitando(false);
      setMensaje('Listo: quitamos la autorización. No se le avisa más a nadie.');
    } catch (err) {
      setError(err.message);
    } finally {
      setGuardando(false);
    }
  };

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
        <h1>Mi familiar autorizado</h1>
        <p className="pac-sub">Elegí a quién avisarle de tus turnos</p>

        {mensaje && <p className="pac-ok" role="status">{mensaje}</p>}
        {error && <p className="pac-error" role="alert">{error}</p>}
        {cargando && <p>Cargando…</p>}

        {!cargando && (
          <>
            <section className="fam-bloque fam-privacidad" aria-labelledby="fam-privacidad-titulo">
              <h2 id="fam-privacidad-titulo">Qué se le avisa</h2>
              <p>Solo cuando un turno se otorga, se reprograma, se cancela, lo confirmás o se acerca la fecha.</p>
              <p><strong>El aviso solo dice tu nombre de pila, que es un turno médico, y el día y la hora.</strong> Nunca se comparte la especialidad, el motivo, tus recetas ni tu medicación.</p>
            </section>

            {familiar && (
              <p className="fam-actual" role="status">
                Autorizaste a <strong>{familiar.nombre}</strong> ({familiar.parentesco}). Le avisamos por {CANALES[familiar.canal]} a <strong>{familiar.contacto}</strong>.
              </p>
            )}

            <form className="fam-bloque fam-form" onSubmit={guardar} noValidate aria-label="Datos del familiar">
              <h2>{familiar ? 'Cambiar los datos' : 'Autorizar a un familiar'}</h2>

              <label>
                Nombre del familiar
                <input type="text" value={form.nombre} maxLength={80} onChange={(e) => cambiar('nombre', e.target.value)} autoComplete="off" />
              </label>
              <label>
                Parentesco
                <input type="text" value={form.parentesco} maxLength={40} placeholder="Hija, hermano, vecina…" onChange={(e) => cambiar('parentesco', e.target.value)} autoComplete="off" />
              </label>
              <label>
                ¿Cómo le avisamos?
                <select value={form.canal} onChange={(e) => cambiar('canal', e.target.value)}>
                  <option value="sms">Mensaje de texto (SMS)</option>
                  <option value="email">Email</option>
                </select>
              </label>
              <label>
                {form.canal === 'email' ? 'Email del familiar' : 'Teléfono del familiar'}
                <input
                  type={form.canal === 'email' ? 'email' : 'tel'}
                  value={form.contacto}
                  maxLength={120}
                  placeholder={form.canal === 'email' ? 'nombre@correo.com' : '+54 9 261 555 1234'}
                  onChange={(e) => cambiar('contacto', e.target.value)}
                  autoComplete="off"
                />
              </label>

              <label className="fam-consentimiento">
                <input type="checkbox" checked={consentimiento} onChange={(e) => setConsentimiento(e.target.checked)} />
                <span>
                  Autorizo que se le avise a esta persona sobre mis turnos médicos (solo día y hora, sin motivo ni especialidad).
                  Puedo quitar esta autorización cuando quiera.
                </span>
              </label>

              <div className="fam-acciones">
                <button type="submit" className="pac-boton pac-boton--primario" disabled={guardando}>
                  {guardando ? 'Guardando…' : familiar ? 'Guardar cambios' : 'Autorizar'}
                </button>
                {familiar && !quitando && (
                  <button type="button" className="pac-boton pac-boton--rechazar" onClick={() => setQuitando(true)}>
                    Quitar autorización
                  </button>
                )}
              </div>

              {quitando && (
                <div className="fam-quitar" role="alertdialog" aria-label="Confirmar que se quita la autorización">
                  <p>¿Seguro que querés dejar de avisarle a {familiar?.nombre}?</p>
                  <div className="fam-acciones">
                    <button type="button" className="pac-boton pac-boton--rechazar" disabled={guardando} onClick={quitar}>
                      Sí, quitar autorización
                    </button>
                    <button type="button" className="pac-boton" onClick={() => setQuitando(false)}>No, volver</button>
                  </div>
                </div>
              )}
            </form>

            <section className="fam-bloque" aria-labelledby="fam-avisos-titulo">
              <h2 id="fam-avisos-titulo">Avisos enviados</h2>
              <p className="fam-ayuda">Acá ves exactamente qué se le mandó a tu familiar.</p>
              {avisos.length === 0 ? (
                <p className="fam-vacio">Todavía no se le envió ningún aviso.</p>
              ) : (
                <ul className="fam-avisos">
                  {avisos.map((a) => (
                    <li key={a.id} className="fam-aviso">
                      <p className="fam-aviso-meta">{CANALES[a.canal] || a.canal} a {a.destino} · {fechaLocal(a.creado_en)}</p>
                      {a.asunto && <p className="fam-aviso-asunto">{a.asunto}</p>}
                      <p className="fam-aviso-texto">{a.texto}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </>
        )}
      </main>
    </div>
  );
}
