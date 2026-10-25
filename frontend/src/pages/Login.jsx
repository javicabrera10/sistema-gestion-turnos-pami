import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const RUTA_POR_ROL = {
  paciente: '/paciente',
  medico: '/medico',
  administrativo: '/admin',
};

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    try {
      const usuario = await login(email, password);
      navigate(RUTA_POR_ROL[usuario.rol] ?? '/login');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: 'linear-gradient(180deg, #0b0f19 0, #0f172a 100%)',
        padding: '1rem',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '400px',
        }}
      >
        <div
          style={{
            textAlign: 'center',
            marginBottom: '2rem',
          }}
        >
          <div
            style={{
              width: '48px',
              height: '48px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #3b82f6 0%, #1e40af 100%)',
              margin: '0 auto 1rem',
            }}
          />
          <h1
            style={{
              margin: '0',
              fontSize: '1.8rem',
              fontWeight: '600',
              color: '#ffffff',
              letterSpacing: '-0.02em',
            }}
          >
            PAMI
          </h1>
          <p
            style={{
              margin: '0.25rem 0 0',
              color: '#94a3b8',
              fontSize: '0.9rem',
            }}
          >
            Sistema de Gestión de Turnos
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            background: '#1e293b',
            padding: '2rem',
            borderRadius: '8px',
            border: '1px solid #334155',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -2px rgba(0, 0, 0, 0.4)',
          }}
        >
          <h2
            style={{
              margin: '0 0 0.5rem',
              fontSize: '1.3rem',
              fontWeight: '600',
              color: '#ffffff',
              textAlign: 'center',
            }}
          >
            Iniciar Sesión
          </h2>
          
          {error && (
            <div
              style={{
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#f87171',
                padding: '0.75rem',
                borderRadius: '6px',
                fontSize: '0.9rem',
              }}
            >
              {error}
            </div>
          )}
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label
              style={{
                fontSize: '0.875rem',
                fontWeight: '500',
                color: '#94a3b8',
              }}
            >
              Correo electrónico
            </label>
            <input
              type="email"
              placeholder="usuario@ejemplo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={{
                padding: '0.65rem',
                borderRadius: '6px',
                border: '1px solid #334155',
                background: '#0f172a',
                color: '#ffffff',
                fontSize: '1rem',
                fontFamily: 'inherit',
              }}
            />
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <label
              style={{
                fontSize: '0.875rem',
                fontWeight: '500',
                color: '#94a3b8',
              }}
            >
              Contraseña
            </label>
            <input
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{
                padding: '0.65rem',
                borderRadius: '6px',
                border: '1px solid #334155',
                background: '#0f172a',
                color: '#ffffff',
                fontSize: '1rem',
                fontFamily: 'inherit',
              }}
            />
          </div>
          
          <button
            type="submit"
            disabled={loading}
            style={{
              padding: '0.7rem',
              borderRadius: '6px',
              border: '1px solid #3b82f6',
              background: loading ? '#475569' : '#3b82f6',
              color: '#ffffff',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontFamily: 'inherit',
              transition: 'all 0.15s ease',
              marginTop: '0.5rem',
            }}
            onMouseOver={(e) => {
              if (!loading) {
                e.target.style.background = '#2563eb';
                e.target.style.borderColor = '#2563eb';
              }
            }}
            onMouseOut={(e) => {
              if (!loading) {
                e.target.style.background = '#3b82f6';
                e.target.style.borderColor = '#3b82f6';
              }
            }}
          >
            {loading ? 'Ingresando...' : 'Ingresar'}
          </button>
        </form>
      </div>
    </div>
  );
}