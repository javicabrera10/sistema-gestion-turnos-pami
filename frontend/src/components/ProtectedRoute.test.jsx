import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAuth } from '../context/AuthContext';
import { ProtectedRoute } from './ProtectedRoute';

// Se simula quién tiene la sesión iniciada
vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }));

// Cada rol y la zona que le corresponde (igual que en App.jsx)
const ZONAS = {
  paciente: { ruta: '/paciente', texto: 'Zona del paciente' },
  medico: { ruta: '/medico', texto: 'Zona del médico' },
  administrativo: { ruta: '/admin', texto: 'Zona del administrativo' },
};

// Todos los cruces: un rol intentando entrar a la zona de otro
const CRUCES = Object.keys(ZONAS).flatMap((rol) =>
  Object.keys(ZONAS)
    .filter((dueno) => dueno !== rol)
    .map((dueno) => [rol, dueno]),
);

function sesion(rol) {
  useAuth.mockReturnValue({ user: rol ? { rol, email: 'prueba@pamiapp.com' } : null });
}

function renderEn(ruta) {
  return render(
    <MemoryRouter initialEntries={[ruta]}>
      <Routes>
        <Route path="/login" element={<p>Pantalla de login</p>} />
        <Route path="/" element={<p>Pantalla de inicio</p>} />
        <Route
          path="/paciente"
          element={<ProtectedRoute allowedRoles={['paciente']}><p>Zona del paciente</p></ProtectedRoute>}
        />
        <Route
          path="/medico"
          element={<ProtectedRoute allowedRoles={['medico']}><p>Zona del médico</p></ProtectedRoute>}
        />
        <Route
          path="/admin"
          element={<ProtectedRoute allowedRoles={['administrativo']}><p>Zona del administrativo</p></ProtectedRoute>}
        />
        <Route path="/cualquiera" element={<ProtectedRoute><p>Zona común</p></ProtectedRoute>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it.each(Object.keys(ZONAS))('sin sesión iniciada, la zona de %s redirige al login', (rol) => {
    sesion(null);
    renderEn(ZONAS[rol].ruta);

    expect(screen.getByText('Pantalla de login')).toBeInTheDocument();
    expect(screen.queryByText(ZONAS[rol].texto)).not.toBeInTheDocument();
  });

  it.each(Object.keys(ZONAS))('un %s entra a su propia zona', (rol) => {
    sesion(rol);
    renderEn(ZONAS[rol].ruta);

    expect(screen.getByText(ZONAS[rol].texto)).toBeInTheDocument();
  });

  it.each(CRUCES)('un %s no puede entrar a la zona de %s y vuelve al inicio', (rol, dueno) => {
    sesion(rol);
    renderEn(ZONAS[dueno].ruta);

    expect(screen.getByText('Pantalla de inicio')).toBeInTheDocument();
    expect(screen.queryByText(ZONAS[dueno].texto)).not.toBeInTheDocument();
  });

  it('si la ruta no pide un rol en particular, entra cualquier usuario con sesión', () => {
    sesion('medico');
    renderEn('/cualquiera');

    expect(screen.getByText('Zona común')).toBeInTheDocument();
  });

  it('si la ruta no pide un rol en particular, sin sesión igual redirige al login', () => {
    sesion(null);
    renderEn('/cualquiera');

    expect(screen.getByText('Pantalla de login')).toBeInTheDocument();
  });
});
