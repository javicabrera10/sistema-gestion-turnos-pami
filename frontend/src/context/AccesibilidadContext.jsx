import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import { useAuth } from './AuthContext';
import '../styles/accesibilidad.css';

const POR_DEFECTO = { tamano_letra: 'normal', alto_contraste: false, voz_activada: true };

const AccesibilidadContext = createContext(null);

export const AccesibilidadProvider = ({ children }) => {
  const { user } = useAuth();
  const email = user?.email ?? null;

  // Lo último que se guardó, junto con la cuenta a la que pertenece (así no se mezclan al cambiar de usuario)
  const [guardadas, setGuardadas] = useState({ email: null, prefs: POR_DEFECTO });
  const preferencias = email && guardadas.email === email ? guardadas.prefs : POR_DEFECTO;

  // Al iniciar sesión se traen las preferencias de la cuenta
  useEffect(() => {
    if (!email) return undefined;
    let activo = true;
    api.get('/usuarios/me/preferencias')
      .then((p) => { if (activo) setGuardadas({ email, prefs: { ...POR_DEFECTO, ...p } }); })
      .catch(() => {}); // si falla, se queda con los valores por defecto
    return () => { activo = false; };
  }, [email]);

  // Se aplican a toda la app con clases en <html> (los estilos están en index.css y accesibilidad.css)
  const { tamano_letra: tamano, alto_contraste: contraste } = preferencias;
  useEffect(() => {
    const html = document.documentElement;
    html.classList.toggle('acc-letra-grande', tamano === 'grande');
    html.classList.toggle('acc-letra-muy-grande', tamano === 'muy_grande');
    html.classList.toggle('acc-alto-contraste', contraste);
  }, [tamano, contraste]);

  // El cambio se ve enseguida; si el servidor lo rechaza, se vuelve a lo anterior
  const cambiar = useCallback(async (parcial) => {
    if (!email) return;
    const anteriores = preferencias;
    const nuevas = { ...anteriores, ...parcial };
    setGuardadas({ email, prefs: nuevas });
    try {
      const confirmadas = await api.put('/usuarios/me/preferencias', nuevas);
      setGuardadas({ email, prefs: { ...POR_DEFECTO, ...confirmadas } });
    } catch (e) {
      setGuardadas({ email, prefs: anteriores });
      throw e;
    }
  }, [email, preferencias]);

  const valor = useMemo(() => ({ preferencias, cambiar }), [preferencias, cambiar]);

  return <AccesibilidadContext.Provider value={valor}>{children}</AccesibilidadContext.Provider>;
};

// eslint-disable-next-line react-refresh/only-export-components
export const useAccesibilidad = () => useContext(AccesibilidadContext);