import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { api } from '../services/api';
import PacienteFamiliar from './PacienteFamiliar';

// La API y la sesión se simulan: estas pruebas no necesitan el backend
vi.mock('../services/api', () => ({ api: { get: vi.fn(), put: vi.fn(), delete: vi.fn(), patch: vi.fn() } }));
vi.mock('../context/AuthContext', () => ({ useAuth: () => ({ user: { nombre: 'Paula Paciente' }, logout: vi.fn() }) }));

const FAMILIAR = {
  id: 'f1',
  paciente_id: 'p1',
  nombre: 'Marta Gómez',
  parentesco: 'Hija',
  canal: 'sms',
  contacto: '+5492615551234',
  autorizado_en: '2026-10-26T12:00:00',
};
const AVISO = {
  id: 'a1',
  canal: 'sms',
  destino: '+5492615551234',
  asunto: '',
  texto: 'Paula tiene un turno médico otorgado para el 05/11/2099 a las 10:30 hs.',
  evento: 'turno.otorgado',
  estado: 'enviado (simulado)',
  creado_en: '2026-10-26T12:00:00',
};

// Simula el backend: cada endpoint devuelve lo que se le pase (la campana pide /notificaciones/mias)
function simular({ familiar = null, avisos = [] } = {}) {
  api.get.mockImplementation(async (url) => {
    if (url === '/familiar') return { familiar };
    if (url === '/familiar/avisos') return avisos;
    return []; // /notificaciones/mias
  });
}

function renderPantalla() {
  return render(
    <MemoryRouter>
      <PacienteFamiliar />
    </MemoryRouter>,
  );
}

async function completar(user, { nombre = 'Marta Gómez', parentesco = 'Hija', contacto = '+54 9 261 555 1234' } = {}) {
  await user.clear(screen.getByLabelText('Nombre del familiar'));
  await user.type(screen.getByLabelText('Nombre del familiar'), nombre);
  await user.clear(screen.getByLabelText('Parentesco'));
  await user.type(screen.getByLabelText('Parentesco'), parentesco);
  await user.clear(screen.getByLabelText(/del familiar$/, { selector: 'input[type=tel], input[type=email]' }));
  await user.type(screen.getByLabelText(/del familiar$/, { selector: 'input[type=tel], input[type=email]' }), contacto);
}

describe('PacienteFamiliar', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('sin familiar muestra el formulario vacío y explica qué se comparte', async () => {
    simular();
    renderPantalla();

    expect(await screen.findByRole('heading', { name: 'Mi familiar autorizado' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Autorizar a un familiar' })).toBeInTheDocument();
    expect(screen.getByLabelText('Nombre del familiar')).toHaveValue('');
    expect(screen.getByText(/Nunca se comparte la especialidad, el motivo, tus recetas ni tu medicación/)).toBeInTheDocument();
    expect(screen.getByText('Todavía no se le envió ningún aviso.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Quitar autorización' })).not.toBeInTheDocument();
  });

  it('autoriza al familiar con el consentimiento y avisa que quedó guardado', async () => {
    simular();
    api.put.mockResolvedValue({ familiar: FAMILIAR });
    const user = userEvent.setup();
    renderPantalla();
    await screen.findByRole('heading', { name: 'Autorizar a un familiar' });

    await completar(user);
    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Autorizar' }));

    expect(api.put).toHaveBeenCalledWith('/familiar', {
      nombre: 'Marta Gómez',
      parentesco: 'Hija',
      canal: 'sms',
      contacto: '+54 9 261 555 1234',
      consentimiento: true,
    });
    expect(await screen.findByText('Listo: a partir de ahora le avisamos a Marta Gómez de tus turnos.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Cambiar los datos' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox')).not.toBeChecked(); // cada cambio vuelve a pedir la autorización
  });

  it('no envía nada si falta el consentimiento', async () => {
    simular();
    const user = userEvent.setup();
    renderPantalla();
    await screen.findByRole('heading', { name: 'Autorizar a un familiar' });

    await completar(user);
    await user.click(screen.getByRole('button', { name: 'Autorizar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Para guardar tenés que marcar que autorizás el aviso.');
    expect(api.put).not.toHaveBeenCalled();
  });

  it.each([
    ['un nombre demasiado corto', { nombre: 'M' }, 'Escribí el nombre del familiar.'],
    ['un parentesco vacío', { parentesco: ' ' }, 'Escribí qué parentesco tiene'],
    ['un teléfono inválido', { contacto: 'abc' }, 'El teléfono del familiar no es válido'],
  ])('avisa si hay %s y no envía el formulario', async (_caso, datos, mensaje) => {
    simular();
    const user = userEvent.setup();
    renderPantalla();
    await screen.findByRole('heading', { name: 'Autorizar a un familiar' });

    await completar(user, datos);
    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Autorizar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(mensaje);
    expect(api.put).not.toHaveBeenCalled();
  });

  it('al elegir email cambia el campo de contacto y valida el email', async () => {
    simular();
    api.put.mockResolvedValue({ familiar: { ...FAMILIAR, canal: 'email', contacto: 'marta@mail.com' } });
    const user = userEvent.setup();
    renderPantalla();
    await screen.findByRole('heading', { name: 'Autorizar a un familiar' });

    await user.selectOptions(screen.getByLabelText('¿Cómo le avisamos?'), 'email');
    expect(screen.getByLabelText('Email del familiar')).toHaveAttribute('type', 'email');

    await completar(user, { contacto: 'marta@' });
    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Autorizar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('El email del familiar no es válido.');
    expect(api.put).not.toHaveBeenCalled();

    await completar(user, { contacto: 'marta@mail.com' });
    await user.click(screen.getByRole('button', { name: 'Autorizar' }));
    expect(api.put).toHaveBeenCalledWith('/familiar', expect.objectContaining({ canal: 'email', contacto: 'marta@mail.com', consentimiento: true }));
  });

  it('muestra el error del servidor si no se pudo guardar', async () => {
    simular();
    api.put.mockRejectedValue(new Error('Datos inválidos'));
    const user = userEvent.setup();
    renderPantalla();
    await screen.findByRole('heading', { name: 'Autorizar a un familiar' });

    await completar(user);
    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: 'Autorizar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Datos inválidos');
  });

  it('con un familiar ya autorizado muestra el resumen y carga sus datos', async () => {
    simular({ familiar: FAMILIAR });
    renderPantalla();

    expect(await screen.findByText(/Autorizaste a/)).toHaveTextContent('Autorizaste a Marta Gómez (Hija). Le avisamos por SMS a +5492615551234.');
    expect(screen.getByLabelText('Nombre del familiar')).toHaveValue('Marta Gómez');
    expect(screen.getByLabelText('Parentesco')).toHaveValue('Hija');
    expect(screen.getByRole('heading', { name: 'Cambiar los datos' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Quitar autorización' })).toBeInTheDocument();
  });

  it('quita la autorización solo después de confirmar', async () => {
    simular({ familiar: FAMILIAR });
    api.delete.mockResolvedValue({ familiar: null });
    const user = userEvent.setup();
    renderPantalla();

    await user.click(await screen.findByRole('button', { name: 'Quitar autorización' }));
    const dialogo = screen.getByRole('alertdialog');
    expect(within(dialogo).getByText('¿Seguro que querés dejar de avisarle a Marta Gómez?')).toBeInTheDocument();
    expect(api.delete).not.toHaveBeenCalled();

    await user.click(within(dialogo).getByRole('button', { name: 'Sí, quitar autorización' }));

    expect(api.delete).toHaveBeenCalledWith('/familiar');
    expect(await screen.findByText('Listo: quitamos la autorización. No se le avisa más a nadie.')).toBeInTheDocument();
    expect(screen.getByLabelText('Nombre del familiar')).toHaveValue('');
    expect(screen.queryByText(/Autorizaste a/)).not.toBeInTheDocument();
  });

  it('se puede volver atrás sin quitar la autorización', async () => {
    simular({ familiar: FAMILIAR });
    const user = userEvent.setup();
    renderPantalla();

    await user.click(await screen.findByRole('button', { name: 'Quitar autorización' }));
    await user.click(screen.getByRole('button', { name: 'No, volver' }));

    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(api.delete).not.toHaveBeenCalled();
  });

  it('lista los avisos enviados para que el paciente vea qué se compartió', async () => {
    simular({
      familiar: FAMILIAR,
      avisos: [
        AVISO,
        { ...AVISO, id: 'a2', canal: 'email', destino: 'marta@mail.com', asunto: 'Aviso de turno médico - App PAMI', texto: 'Hola Marta Gómez:\n\nPaula confirmó su turno médico.' },
      ],
    });
    renderPantalla();

    expect(await screen.findByText('Paula tiene un turno médico otorgado para el 05/11/2099 a las 10:30 hs.')).toBeInTheDocument();
    expect(screen.getByText(/SMS a \+5492615551234/)).toBeInTheDocument();
    expect(screen.getByText(/Email a marta@mail.com/)).toBeInTheDocument();
    expect(screen.getByText('Aviso de turno médico - App PAMI')).toBeInTheDocument();
    expect(screen.queryByText('Todavía no se le envió ningún aviso.')).not.toBeInTheDocument();
  });

  it('muestra un error si no se pueden cargar los datos', async () => {
    api.get.mockRejectedValue(new Error('sin conexión'));
    renderPantalla();

    expect(await screen.findByRole('alert')).toHaveTextContent('sin conexión');
  });
});
