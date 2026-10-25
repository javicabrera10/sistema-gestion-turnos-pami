import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider } from '../context/AuthContext';
import { api } from '../services/api';
import Login from './Login';

// La API se simula: estas pruebas no necesitan el backend
vi.mock('../services/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn() },
}));

const EMAIL = 'paula@pamiapp.com';
const PASSWORD = 'Paciente1234';

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/paciente" element={<p>Inicio del paciente</p>} />
          <Route path="/medico" element={<p>Panel del médico</p>} />
          <Route path="/admin" element={<p>Panel administrativo</p>} />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  );
}

async function completarYEnviar(user) {
  await user.type(await screen.findByLabelText('Correo electrónico'), EMAIL);
  await user.type(screen.getByLabelText('Contraseña'), PASSWORD);
  await user.click(screen.getByRole('button', { name: 'Ingresar' }));
}

describe('Login', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    localStorage.clear();
  });

  it('muestra el formulario con los dos campos obligatorios', async () => {
    renderLogin();

    expect(await screen.findByRole('heading', { name: 'Iniciar Sesión' })).toBeInTheDocument();
    expect(screen.getByLabelText('Correo electrónico')).toBeRequired();
    expect(screen.getByLabelText('Contraseña')).toBeRequired();
    expect(screen.getByLabelText('Contraseña')).toHaveAttribute('type', 'password');
    expect(screen.getByRole('button', { name: 'Ingresar' })).toBeEnabled();
  });

  it('muestra el error cuando las credenciales son incorrectas', async () => {
    api.post.mockRejectedValue(new Error('Email o contraseña incorrectos'));
    const user = userEvent.setup();
    renderLogin();

    await completarYEnviar(user);

    expect(await screen.findByRole('alert')).toHaveTextContent('Email o contraseña incorrectos');
    expect(api.post).toHaveBeenCalledWith('/auth/login', { email: EMAIL, password: PASSWORD });
    // sigue en el login, sin sesión iniciada y con el botón disponible otra vez
    expect(screen.getByRole('heading', { name: 'Iniciar Sesión' })).toBeInTheDocument();
    expect(localStorage.getItem('token')).toBeNull();
    expect(screen.getByRole('button', { name: 'Ingresar' })).toBeEnabled();
  });

  it('muestra el mensaje del servidor cuando la cuenta está bloqueada', async () => {
    api.post.mockRejectedValue(new Error('Cuenta bloqueada temporalmente por intentos fallidos'));
    const user = userEvent.setup();
    renderLogin();

    await completarYEnviar(user);

    expect(await screen.findByRole('alert')).toHaveTextContent('Cuenta bloqueada temporalmente');
    expect(localStorage.getItem('token')).toBeNull();
  });

  it.each([
    ['paciente', 'Inicio del paciente'],
    ['medico', 'Panel del médico'],
    ['administrativo', 'Panel administrativo'],
  ])('un %s entra a su pantalla y se guarda la sesión', async (rol, pantalla) => {
    api.post.mockResolvedValue({ access_token: 'token-de-prueba', rol, nombre: 'Persona de Prueba' });
    const user = userEvent.setup();
    renderLogin();

    await completarYEnviar(user);

    expect(await screen.findByText(pantalla)).toBeInTheDocument();
    expect(localStorage.getItem('token')).toBe('token-de-prueba');
  });

  it('deshabilita el botón mientras espera la respuesta', async () => {
    let responder;
    api.post.mockReturnValue(
      new Promise((resolve) => {
        responder = resolve;
      }),
    );
    const user = userEvent.setup();
    renderLogin();

    await completarYEnviar(user);

    expect(await screen.findByRole('button', { name: 'Ingresando...' })).toBeDisabled();

    responder({ access_token: 'token-de-prueba', rol: 'paciente', nombre: 'Paula' });
    expect(await screen.findByText('Inicio del paciente')).toBeInTheDocument();
  });
});
