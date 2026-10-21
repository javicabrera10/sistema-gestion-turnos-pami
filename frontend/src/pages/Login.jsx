import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    try {
      // login() del AuthContext devuelve los datos del usuario
      // (Asumimos que el backend devuelve el rol en la respuesta)
      await login(email, password); 
      
      // Como el AuthContext actualiza el usuario de forma asíncrona,
      // podemos redirigir basándonos en el email o forzando un pequeño timeout.
      // Para simplificar ahora: si es medico@pamiapp.com, vamos a /medico
      
      if (email === 'medico@pamiapp.com') {
        navigate('/medico');
      } else if (email === 'admin@pamiapp.com') {
        navigate('/admin');
      } else {
        navigate('/paciente');
      }

    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '300px' }}>
        <h2>Iniciar Sesión - PAMI</h2>
        {error && <p style={{ color: 'red' }}>{error}</p>}
        <input type="email" placeholder="Correo" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input type="password" placeholder="Contraseña" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button type="submit">Ingresar</button>
      </form>
    </div>
  );
}