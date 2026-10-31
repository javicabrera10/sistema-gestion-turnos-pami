import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import MedicoRecetas from './MedicoRecetas';

// La API y la sesión se simulan: estas pruebas no necesitan el backend
vi.mock('../services/api', () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: { nombre: 'Martín Médico' }, logout: vi.fn() }) }));

const PACIENTE = { id: 'p1', nombre: 'Paula Paciente', dni: '12345678' };

// Elige al paciente por DNI y completa un medicamento (Ibuprofeno 400 mg, cada 8 horas)
async function prepararReceta(user) {
  await user.type(screen.getByLabelText('DNI del paciente'), '12345678');
  await user.click(screen.getByRole('button', { name: 'Buscar' }));
  await screen.findByText(/Paula Paciente/);
  await user.type(screen.getByLabelText('Nombre'), 'Ibuprofeno');
  await user.type(screen.getByLabelText('Dosis'), '400 mg');
  await user.type(screen.getByLabelText('Horario'), 'Cada 8 horas');
}

// Los inputs de hora y de número se llenan con fireEvent: es lo que dispara el cambio igual que en el navegador
function poner(etiqueta, valor) {
  fireEvent.change(screen.getByLabelText(etiqueta), { target: { value: valor } });
}

async function agregarHorarios(user, horas) {
  for (let i = 0; i < horas.length; i += 1) {
    await user.click(screen.getByRole('button', { name: '+ Agregar horario' }));
    poner(`Horario ${i + 1} del medicamento 1`, horas[i]);
  }
}

describe('MedicoRecetas: plan de medicación', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.get.mockResolvedValue([PACIENTE]);
    api.post.mockImplementation(async (url) => (url === '/recetas' ? { id: 'r1' } : {}));
    api.put.mockResolvedValue({});
  });

  it('emite una receta con horarios y duración: crea, carga el plan y recién después emite', async () => {
    const user = userEvent.setup();
    render(<MedicoRecetas />);
    await prepararReceta(user);

    await agregarHorarios(user, ['16:00', '08:00', '00:00']);
    poner('Duración (días)', '7');
    await user.click(screen.getByRole('button', { name: 'Emitir receta al paciente' }));

    expect(await screen.findByText(/Receta emitida al paciente\. El administrativo va a generar el recordatorio de toma para el paciente\./)).toBeInTheDocument();
    expect(api.post).toHaveBeenNthCalledWith(1, '/recetas', expect.objectContaining({ paciente_id: 'p1', tipo: 'receta' }));
    expect(api.put).toHaveBeenCalledWith('/recetas/r1/plan', {
      plan: [{ medicamento: 'Ibuprofeno', dosis: '400 mg', horarios: ['00:00', '08:00', '16:00'], duracion_dias: 7 }],
    });
    expect(api.post).toHaveBeenNthCalledWith(2, '/recetas/r1/emitir');
    // el plan se carga antes de emitir: el tratamiento empieza a contar al emitir
    expect(api.put.mock.invocationCallOrder[0]).toBeLessThan(api.post.mock.invocationCallOrder[1]);
    expect(screen.getByText(/con aviso de toma/)).toBeInTheDocument();
  });

  it('sin horarios no carga ningún plan y la receta se emite igual', async () => {
    const user = userEvent.setup();
    render(<MedicoRecetas />);
    await prepararReceta(user);

    await user.click(screen.getByRole('button', { name: 'Emitir receta al paciente' }));

    expect(await screen.findByText('Receta emitida al paciente.')).toBeInTheDocument();
    expect(api.put).not.toHaveBeenCalled();
    expect(api.post).toHaveBeenCalledWith('/recetas/r1/emitir');
  });

  it('guarda el borrador con su plan sin emitirlo', async () => {
    const user = userEvent.setup();
    render(<MedicoRecetas />);
    await prepararReceta(user);

    await agregarHorarios(user, ['08:00']);
    poner('Duración (días)', '3');
    await user.click(screen.getByRole('button', { name: 'Guardar borrador' }));

    expect(await screen.findByText('Receta guardada como borrador.')).toBeInTheDocument();
    expect(api.put).toHaveBeenCalledWith('/recetas/r1/plan', expect.anything());
    expect(api.post).not.toHaveBeenCalledWith('/recetas/r1/emitir');
  });

  it('se pueden quitar horarios y cada medicamento tiene los suyos', async () => {
    const user = userEvent.setup();
    render(<MedicoRecetas />);

    await agregarHorarios(user, ['08:00', '20:00']);
    await user.click(screen.getByRole('button', { name: 'Quitar horario 1 del medicamento 1' }));

    expect(screen.getAllByLabelText(/^Horario \d del medicamento 1$/)).toHaveLength(1);
    expect(screen.getByLabelText('Horario 1 del medicamento 1')).toHaveValue('20:00');

    await user.click(screen.getByRole('button', { name: '+ Agregar otro medicamento' }));
    expect(screen.queryByLabelText('Horario 1 del medicamento 2')).not.toBeInTheDocument();
  });

  it('no deja agregar más de 12 horarios', async () => {
    const user = userEvent.setup();
    render(<MedicoRecetas />);

    for (let i = 0; i < 12; i += 1) await user.click(screen.getByRole('button', { name: '+ Agregar horario' }));

    expect(screen.getByRole('button', { name: '+ Agregar horario' })).toBeDisabled();
  });

  it.each([
    ['horarios sin duración', async (user) => agregarHorarios(user, ['08:00']), /cargá los horarios y la duración, o dejá los dos vacíos/],
    ['duración sin horarios', async () => poner('Duración (días)', '5'), /cargá los horarios y la duración, o dejá los dos vacíos/],
    ['un horario sin completar', async (user) => { await user.click(screen.getByRole('button', { name: '+ Agregar horario' })); poner('Duración (días)', '5'); }, /Completá todos los horarios de Ibuprofeno/],
    ['horarios repetidos', async (user) => { await agregarHorarios(user, ['08:00', '08:00']); poner('Duración (días)', '5'); }, /Hay horarios repetidos en Ibuprofeno/],
    ['una duración de 0 días', async (user) => { await agregarHorarios(user, ['08:00']); poner('Duración (días)', '0'); }, /tiene que ser de 1 a 365 días/],
    ['una duración de más de un año', async (user) => { await agregarHorarios(user, ['08:00']); poner('Duración (días)', '400'); }, /tiene que ser de 1 a 365 días/],
  ])('avisa si hay %s y no crea nada', async (_caso, preparar, mensaje) => {
    const user = userEvent.setup();
    render(<MedicoRecetas />);
    await prepararReceta(user);

    await preparar(user);
    await user.click(screen.getByRole('button', { name: 'Emitir receta al paciente' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(mensaje);
    expect(api.post).not.toHaveBeenCalled();
    expect(api.put).not.toHaveBeenCalled();
  });

  it('si no se puede cargar el plan, la receta queda como borrador y no se emite', async () => {
    api.put.mockRejectedValue(new Error('Datos inválidos'));
    const user = userEvent.setup();
    render(<MedicoRecetas />);
    await prepararReceta(user);

    await agregarHorarios(user, ['08:00']);
    poner('Duración (días)', '5');
    await user.click(screen.getByRole('button', { name: 'Emitir receta al paciente' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('La receta quedó guardada como borrador, pero no se pudo cargar el plan de toma: Datos inválidos');
    expect(api.post).not.toHaveBeenCalledWith('/recetas/r1/emitir');
    const historial = screen.getByRole('region', { name: 'Creadas en esta sesión' });
    expect(within(historial).getByText('Borrador')).toBeInTheDocument();
  });

  it('una orden no muestra el aviso de toma ni carga ningún plan', async () => {
    const user = userEvent.setup();
    render(<MedicoRecetas />);

    await user.click(screen.getByRole('tab', { name: /Orden/ }));

    expect(screen.queryByText('Aviso de toma al paciente')).not.toBeInTheDocument();
    expect(api.put).not.toHaveBeenCalled();
  });
});
