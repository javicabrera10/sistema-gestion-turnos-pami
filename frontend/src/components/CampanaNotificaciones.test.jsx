import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import CampanaNotificaciones from './CampanaNotificaciones';

// La API se simula: estas pruebas no necesitan el backend
vi.mock('../services/api', () => ({ api: { get: vi.fn(), patch: vi.fn() } }));

const AVISOS = [
  { id: 'n1', tipo: 'toma_medicacion', mensaje: 'Tu médico te emitió una receta. Plan de toma: Ibuprofeno (400 mg) a las 08:00 hs durante 5 días.', leida: false, creada_en: '2026-10-26T11:00:00' },
  { id: 'n2', tipo: 'turno_cancelado', mensaje: 'Cancelaron tu turno de Cardiología.', leida: true, creada_en: '2026-10-25T14:00:00' },
];

describe('CampanaNotificaciones', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('muestra cuántos avisos hay sin leer', async () => {
    api.get.mockResolvedValue(AVISOS);
    render(<CampanaNotificaciones />);

    expect(await screen.findByRole('button', { name: 'Avisos, 1 sin leer' })).toBeInTheDocument();
    expect(api.get).toHaveBeenCalledWith('/notificaciones/mias');
  });

  it('abre el panel con los avisos y el ícono de cada tipo', async () => {
    api.get.mockResolvedValue(AVISOS);
    const user = userEvent.setup();
    render(<CampanaNotificaciones />);

    await user.click(await screen.findByRole('button', { name: /Avisos/ }));

    expect(screen.getByText('Tu médico te emitió una receta. Plan de toma: Ibuprofeno (400 mg) a las 08:00 hs durante 5 días.')).toBeInTheDocument();
    expect(screen.getByText('Cancelaron tu turno de Cardiología.')).toBeInTheDocument();
    expect(screen.getByText('💊')).toBeInTheDocument(); // receta con plan de toma
    expect(screen.getByText('❌')).toBeInTheDocument(); // turno cancelado
  });

  it('muestra al administrativo el aviso de receta emitida con su propio ícono', async () => {
    api.get.mockResolvedValue([
      {
        id: 'n3',
        tipo: 'receta_emitida',
        mensaje: 'Martín Médico emitió una receta con plan de medicación para Paula Paciente. Tocá «Generar recordatorios» para que el paciente reciba su receta y el aviso de toma.',
        leida: false,
        creada_en: '2026-10-28T15:00:00',
      },
    ]);
    const user = userEvent.setup();
    render(<CampanaNotificaciones />);

    await user.click(await screen.findByRole('button', { name: 'Avisos, 1 sin leer' }));

    expect(screen.getByText(/emitió una receta con plan de medicación para Paula Paciente/)).toBeInTheDocument();
    expect(screen.getByText('📝')).toBeInTheDocument();
  });

  it('marca un aviso como leído y baja el contador', async () => {
    api.get.mockResolvedValue(AVISOS);
    api.patch.mockResolvedValue({ ...AVISOS[0], leida: true });
    const user = userEvent.setup();
    render(<CampanaNotificaciones />);

    await user.click(await screen.findByRole('button', { name: 'Avisos, 1 sin leer' }));
    await user.click(screen.getByRole('button', { name: 'Marcar como leída' }));

    await waitFor(() => expect(api.patch).toHaveBeenCalledWith('/notificaciones/n1/leida'));
    expect(await screen.findByRole('button', { name: 'Avisos' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Marcar como leída' })).not.toBeInTheDocument();
  });

  it('avisa cuando no hay nada y se cierra con Escape', async () => {
    api.get.mockResolvedValue([]);
    const user = userEvent.setup();
    render(<CampanaNotificaciones />);

    await user.click(await screen.findByRole('button', { name: 'Avisos' }));
    expect(screen.getByText('No tenés avisos por ahora.')).toBeInTheDocument();

    await user.keyboard('{Escape}');
    expect(screen.queryByText('No tenés avisos por ahora.')).not.toBeInTheDocument();
  });

  it('muestra un error si no se pueden cargar', async () => {
    api.get.mockRejectedValue(new Error('sin conexión'));
    const user = userEvent.setup();
    render(<CampanaNotificaciones />);

    await user.click(await screen.findByRole('button', { name: 'Avisos' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar tus avisos.');
  });
});
