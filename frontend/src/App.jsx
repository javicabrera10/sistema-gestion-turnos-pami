import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import Login from './pages/Login';
import PacienteInicio from './pages/PacienteInicio';
import MisTurnos from './pages/MisTurnos';
import SolicitarTurno from './pages/SolicitarTurno';
import MedicoRecetas from './pages/MedicoRecetas';
import AdminTurnos from './pages/AdminTurnos';

const soloPaciente = (pagina) => <ProtectedRoute allowedRoles={['paciente']}>{pagina}</ProtectedRoute>;

function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/paciente" element={soloPaciente(<PacienteInicio />)} />
          <Route path="/paciente/turnos" element={soloPaciente(<MisTurnos />)} />
          <Route path="/paciente/turnos/nuevo" element={soloPaciente(<SolicitarTurno />)} />
          <Route path="/medico" element={<ProtectedRoute allowedRoles={['medico']}><MedicoRecetas /></ProtectedRoute>} />
          <Route path="/admin" element={<ProtectedRoute allowedRoles={['administrativo']}><AdminTurnos /></ProtectedRoute>} />
          <Route path="/" element={<Navigate to="/login" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
