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

  it('informa los recordatorios de turno y los avisos de toma que se generaron', async () => {
    api.post.mockResolvedValue({ enviados: 2, tomas: 1 });
    const user = userEvent.setup();
    renderPanel();

    await generar(user);

    expect(api.post).toHaveBeenCalledWith('/recordatorios/ejecutar');
    expect(await screen.findByText(/Se generaron: 2 recordatorios de turno y 1 aviso de toma de medicación/)).toBeInTheDocument();
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
