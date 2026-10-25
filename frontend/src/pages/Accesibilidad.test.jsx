import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AccesibilidadProvider } from '../context/AccesibilidadContext';
import { api } from '../services/api';
import Accesibilidad from './Accesibilidad';

// La sesión se simula: se cambia el usuario según la prueba
const auth = vi.hoisted(() => ({ user: null }));
vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: auth.user, logout: vi.fn() }),
}));

// La API se simula: estas pruebas no necesitan el backend
vi.mock('../services/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() },
}));

const RUTA_PREFERENCIAS = '/usuarios/me/preferencias';
const POR_DEFECTO = { tamano_letra: 'normal', alto_contraste: false, voz_activada: true };

function renderAccesibilidad() {
  return render(
    <MemoryRouter>
      <AccesibilidadProvider>
        <Accesibilidad />
      </AccesibilidadProvider>
    </MemoryRouter>,
  );
}

const interruptor = (nombre) => screen.getByRole('switch', { name: nombre });
const opcion = (nombre) => screen.getByRole('radio', { name: nombre });

describe('Accesibilidad', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    auth.user = { email: 'paula@pamiapp.com', nombre: 'Paula', rol: 'paciente' };
    api.get.mockResolvedValue(POR_DEFECTO);
    // El servidor confirma lo que recibe
    api.put.mockImplementation(async (_ruta, cuerpo) => cuerpo);
    document.documentElement.className = '';
  });

  afterEach(() => {
    cleanup();
    document.documentElement.className = '';
  });

  it('muestra las preferencias guardadas en el servidor', async () => {
    api.get.mockResolvedValue({ tamano_letra: 'grande', alto_contraste: true, voz_activada: false });
    renderAccesibilidad();

    await waitFor(() => expect(opcion('Grande')).toBeChecked());
    expect(api.get).toHaveBeenCalledWith(RUTA_PREFERENCIAS);
    expect(opcion('Normal')).not.toBeChecked();
    expect(interruptor(/Alto contraste/)).toBeChecked();
    expect(interruptor(/Pedir turnos con la voz/)).not.toBeChecked();
  });

  it('aplica las preferencias guardadas a <html> al cargar', async () => {
    api.get.mockResolvedValue({ tamano_letra: 'muy_grande', alto_contraste: true, voz_activada: true });
    renderAccesibilidad();

    await waitFor(() => expect(document.documentElement).toHaveClass('acc-letra-muy-grande'));
    expect(document.documentElement).toHaveClass('acc-alto-contraste');
  });

  it('si no se pueden traer las preferencias, usa los valores por defecto', async () => {
    api.get.mockRejectedValue(new Error('sin conexión'));
    renderAccesibilidad();

    await waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(opcion('Normal')).toBeChecked();
    expect(interruptor(/Alto contraste/)).not.toBeChecked();
    expect(interruptor(/Pedir turnos con la voz/)).toBeChecked();
  });

  it('cambiar el tamaño de letra lo guarda en el servidor y lo aplica a <html>', async () => {
    const user = userEvent.setup();
    renderAccesibilidad();
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    await user.click(opcion('Muy grande'));

    await waitFor(() => expect(api.put).toHaveBeenCalledWith(RUTA_PREFERENCIAS, {
      ...POR_DEFECTO,
      tamano_letra: 'muy_grande',
    }));
    expect(opcion('Muy grande')).toBeChecked();
    expect(document.documentElement).toHaveClass('acc-letra-muy-grande');
    expect(await screen.findByText('Listo, guardamos tu elección.')).toBeInTheDocument();
  });

  it('el tamaño grande aplica su clase y quita la anterior', async () => {
    const user = userEvent.setup();
    renderAccesibilidad();
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    await user.click(opcion('Muy grande'));
    await waitFor(() => expect(document.documentElement).toHaveClass('acc-letra-muy-grande'));
    await user.click(opcion('Grande'));

    await waitFor(() => expect(document.documentElement).toHaveClass('acc-letra-grande'));
    expect(document.documentElement).not.toHaveClass('acc-letra-muy-grande');
  });

  it('activar el alto contraste lo guarda en el servidor y lo aplica a <html>', async () => {
    const user = userEvent.setup();
    renderAccesibilidad();
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    await user.click(interruptor(/Alto contraste/));

    await waitFor(() => expect(api.put).toHaveBeenCalledWith(RUTA_PREFERENCIAS, {
      ...POR_DEFECTO,
      alto_contraste: true,
    }));
    expect(interruptor(/Alto contraste/)).toBeChecked();
    expect(document.documentElement).toHaveClass('acc-alto-contraste');
  });

  it('desactivar la voz lo guarda en el servidor', async () => {
    const user = userEvent.setup();
    renderAccesibilidad();
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    await user.click(interruptor(/Pedir turnos con la voz/));

    await waitFor(() => expect(api.put).toHaveBeenCalledWith(RUTA_PREFERENCIAS, {
      ...POR_DEFECTO,
      voz_activada: false,
    }));
    expect(interruptor(/Pedir turnos con la voz/)).not.toBeChecked();
  });

  it('si el servidor rechaza el cambio, vuelve atrás y muestra el error', async () => {
    api.put.mockRejectedValue(new Error('No se pudo guardar tu elección'));
    const user = userEvent.setup();
    renderAccesibilidad();
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    await user.click(opcion('Grande'));

    expect(await screen.findByText('No se pudo guardar tu elección')).toBeInTheDocument();
    expect(opcion('Normal')).toBeChecked();
    expect(opcion('Grande')).not.toBeChecked();
    expect(document.documentElement).not.toHaveClass('acc-letra-grande');
    expect(screen.queryByText('Listo, guardamos tu elección.')).not.toBeInTheDocument();
  });

  it.each([
    ['paciente', '/paciente'],
    ['medico', '/medico'],
    ['administrativo', '/admin'],
  ])('el enlace "Inicio" de un %s va a %s', async (rol, ruta) => {
    auth.user = { email: 'usuario@pamiapp.com', nombre: 'Usuario', rol };
    renderAccesibilidad();
    await waitFor(() => expect(api.get).toHaveBeenCalled());

    expect(screen.getByRole('link', { name: '← Inicio' })).toHaveAttribute('href', ruta);
  });
});
