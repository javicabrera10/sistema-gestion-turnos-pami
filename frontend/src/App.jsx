import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import Login from './pages/Login';
import MedicoRecetas from './pages/MedicoRecetas';
import SolicitarTurno from './pages/SolicitarTurno';

const DashboardPaciente = () => (
  <div>
    Dashboard Paciente (Javier)
    <p><Link to="/paciente/turnos/nuevo">Pedir un turno</Link></p>
  </div>
);
const DashboardAdmin = () => <div>Dashboard Administrativo (Javier)</div>;

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/paciente" element={<ProtectedRoute allowedRoles={['paciente']}><DashboardPaciente /></ProtectedRoute>} />
          <Route path="/paciente/turnos/nuevo" element={<ProtectedRoute allowedRoles={['paciente']}><SolicitarTurno /></ProtectedRoute>} />
          <Route path="/medico" element={<ProtectedRoute allowedRoles={['medico']}><MedicoRecetas /></ProtectedRoute>} />
          <Route path="/admin" element={<ProtectedRoute allowedRoles={['administrativo']}><DashboardAdmin /></ProtectedRoute>} />
          <Route path="/" element={<Navigate to="/login" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;