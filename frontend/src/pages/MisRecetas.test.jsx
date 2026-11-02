import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import MisRecetas from './MisRecetas';

vi.mock('../services/api', () => ({ api: { get: vi.fn() } }));
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: { nombre: 'Paula Paciente' }, logout: vi.fn() }) }));
vi.mock('../components/CampanaNotificaciones', () => ({ default: () => null }));

const RECETA = {
  id: 'r1',
  tipo: 'receta',
  fecha: '2026-10-28T14:30:00',
  indicaciones: 'Después de las comidas',
  medicamentos: [{ nombre: 'Ibuprofeno', dosis: '400 mg', presentacion: 'Comprimidos', horario_toma: '' }],
  plan_medicacion: [{ medicamento: 'Ibuprofeno', dosis: '400 mg', horarios: ['08:00', '20:00'], duracion_dias: 5 }],
};
const ORDEN = { id: 'o1', tipo: 'orden', fecha: '2026-10-28T14:30:00', indicaciones: 'Análisis de sangre completo', medicamentos: [], plan_medicacion: [] };

function renderPagina() {
  return render(
    <MemoryRouter>
      <MisRecetas />
    </MemoryRouter>,
  );
}

describe('MisRecetas', () => {
  beforeEach(() => vi.resetAllMocks());

  it('muestra la receta con sus medicamentos, el plan de toma y las indicaciones', async () => {
    api.get.mockResolvedValue([RECETA]);
    renderPagina();

    // el medicamento aparece dos veces: en la lista de medicamentos y en el plan de toma
    expect(await screen.findAllByText('Ibuprofeno', { selector: 'strong' })).toHaveLength(2);
    expect(api.get).toHaveBeenCalledWith('/recetas/mias');
    expect(screen.getByText(/a las 08:00, 20:00 hs durante 5 días/)).toBeInTheDocument();
    expect(screen.getByText(/Indicaciones: Después de las comidas/)).toBeInTheDocument();
  });

  it('muestra el pedido de estudios con lo que tiene que hacerse', async () => {
    api.get.mockResolvedValue([ORDEN]);
    renderPagina();

    expect(await screen.findByRole('heading', { name: 'Pedido de estudios' })).toBeInTheDocument();
    expect(screen.getByText(/Qué tenés que hacerte: Análisis de sangre completo/)).toBeInTheDocument();
  });

  it('avisa cuando todavía no hay nada', async () => {
    api.get.mockResolvedValue([]);
    renderPagina();

    expect(await screen.findByText('Todavía no tenés recetas ni pedidos de estudios.')).toBeInTheDocument();
  });

  it('muestra el error si no se pueden traer', async () => {
    api.get.mockRejectedValue(new Error('El rol no tiene permiso'));
    renderPagina();

    expect(await screen.findByRole('alert')).toHaveTextContent('El rol no tiene permiso');
  });
});
