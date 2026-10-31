import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import AdminTurnos from './AdminTurnos';

// La API y la sesión se simulan: estas pruebas no necesitan el backend
vi.mock('../services/api', () => ({ api: { get: vi.fn(), post: vi.fn(), patch: vi.fn() } }));
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: { nombre: 'Ana Admin' }, logout: vi.fn() }) }));

function renderPanel() {
  return render(
    <MemoryRouter>
      <AdminTurnos />
    </MemoryRouter>,
  );
}

async function generar(user) {
  await user.click(await screen.findByRole('button', { name: /Generar recordatorios/ }));
}

describe('AdminTurnos: botón Generar recordatorios', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.get.mockResolvedValue([]);
  });

  it('informa los recordatorios de turno y las recetas con plan de toma que se entregaron', async () => {
    api.post.mockResolvedValue({ enviados: 2, tomas: 1 });
    const user = userEvent.setup();
    renderPanel();

    await generar(user);

    expect(api.post).toHaveBeenCalledWith('/recordatorios/ejecutar');
    expect(await screen.findByText(/Se generaron: 2 recordatorios de turno y 1 receta con plan de toma/)).toBeInTheDocument();
  });

  it('usa el singular y nombra solo lo que se generó', async () => {
    api.post.mockResolvedValue({ enviados: 1, tomas: 0 });
    const user = userEvent.setup();
    renderPanel();

    await generar(user);

    expect(await screen.findByText(/Se generaron: 1 recordatorio de turno\./)).toBeInTheDocument();
  });

  it('avisa cuando no hay nada nuevo', async () => {
    api.post.mockResolvedValue({ enviados: 0, tomas: 0 });
    const user = userEvent.setup();
    renderPanel();

    await generar(user);

    expect(await screen.findByText('No hay recordatorios nuevos para enviar.')).toBeInTheDocument();
  });

  it('muestra el error si el servidor lo rechaza', async () => {
    api.post.mockRejectedValue(new Error('El rol no tiene permiso'));
    const user = userEvent.setup();
    renderPanel();

    await generar(user);

    expect(await screen.findByRole('alert')).toHaveTextContent('El rol no tiene permiso');
  });
});

const RECETA = {
  id: 'r1',
  tipo: 'receta',
  fecha: '2026-10-28T14:30:00',
  con_plan: true,
  recordatorio_generado_en: null,
  paciente: { id: 'p1', nombre: 'Paula Paciente', dni: '30111222', telefono: '2610000003' },
  medico: { id: 'm1', nombre: 'Martín Médico', especialidad: 'Clínica médica' },
};

// Cada ruta devuelve lo suyo: los turnos y los médicos vacíos, las recetas emitidas las que se pidan
function simularApi(recetas) {
  api.get.mockImplementation((ruta) => Promise.resolve(ruta === '/recetas/emitidas' ? recetas : []));
}

describe('AdminTurnos: turnos y recetas', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('el título es «Turnos y recetas»', async () => {
    simularApi([]);
    renderPanel();

    expect(await screen.findByRole('heading', { level: 1, name: 'Turnos y recetas' })).toBeInTheDocument();
  });

  it('muestra las recetas emitidas con los datos del paciente y del médico', async () => {
    simularApi([RECETA]);
    const user = userEvent.setup();
    renderPanel();

    await user.click(await screen.findByRole('tab', { name: /Recetas emitidas/ }));

    expect(api.get).toHaveBeenCalledWith('/recetas/emitidas');
    expect(screen.getByText('Paula Paciente')).toBeInTheDocument();
    expect(screen.getByText(/DNI 30111222 · Tel\. 2610000003/)).toBeInTheDocument();
    expect(screen.getByText(/Martín Médico · Clínica médica/)).toBeInTheDocument();
    expect(screen.getByText('Recordatorio pendiente')).toBeInTheDocument();
  });

  it('distingue la receta ya entregada y la que no tiene plan de toma', async () => {
    simularApi([
      { ...RECETA, id: 'r2', recordatorio_generado_en: '2026-10-28T15:00:00' },
      { ...RECETA, id: 'r3', tipo: 'orden', con_plan: false },
    ]);
    const user = userEvent.setup();
    renderPanel();

    await user.click(await screen.findByRole('tab', { name: /Recetas emitidas/ }));

    expect(screen.getByText('Recordatorio generado')).toBeInTheDocument();
    expect(screen.getByText('Sin plan de toma')).toBeInTheDocument();
    expect(screen.getByText('Orden')).toBeInTheDocument();
  });

  it('avisa cuando todavía no hay recetas emitidas', async () => {
    simularApi([]);
    const user = userEvent.setup();
    renderPanel();

    await user.click(await screen.findByRole('tab', { name: /Recetas emitidas/ }));

    expect(screen.getByText('Los médicos todavía no emitieron recetas.')).toBeInTheDocument();
  });

  it('al generar los recordatorios desde las recetas se actualiza el estado', async () => {
    api.get.mockImplementation((ruta) => Promise.resolve(ruta === '/recetas/emitidas' ? [RECETA] : []));
    api.post.mockResolvedValue({ enviados: 0, tomas: 1 });
    const user = userEvent.setup();
    renderPanel();
    await user.click(await screen.findByRole('tab', { name: /Recetas emitidas/ }));
    expect(screen.getByText('Recordatorio pendiente')).toBeInTheDocument();

    api.get.mockImplementation((ruta) =>
      Promise.resolve(ruta === '/recetas/emitidas' ? [{ ...RECETA, recordatorio_generado_en: '2026-10-28T15:00:00' }] : []),
    );
    await generar(user);

    expect(await screen.findByText('Recordatorio generado')).toBeInTheDocument();
  });

  it('si no se pueden traer las recetas, los turnos se siguen viendo', async () => {
    api.get.mockImplementation((ruta) => (ruta === '/recetas/emitidas' ? Promise.reject(new Error('x')) : Promise.resolve([])));
    renderPanel();

    expect(await screen.findByText('No hay turnos en esta categoría.')).toBeInTheDocument();
  });
});
