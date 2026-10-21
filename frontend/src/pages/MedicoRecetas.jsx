import { useState } from 'react';
import { api } from '../services/api';

export default function MedicoRecetas() {
  const [pacienteId, setPacienteId] = useState('');
  const [medicamentos, setMedicamentos] = useState([{ nombre: '', dosis: '', horario_toma: '' }]);
  const [mensaje, setMensaje] = useState('');

  const agregarMedicamento = () => {
    setMedicamentos([...medicamentos, { nombre: '', dosis: '', horario_toma: '' }]);
  };

  const handleMedChange = (index, field, value) => {
    const nuevos = [...medicamentos];
    nuevos[index][field] = value;
    setMedicamentos(nuevos);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = await api.post('/recetas', {
        paciente_id: pacienteId,
        medicamentos: medicamentos
      });
      setMensaje('Receta creada con éxito. ID: ' + data.id);
      // Opcional: podríamos llamar a /recetas/{id}/emitir acá mismo
    } catch (error) {
      setMensaje('Error: ' + error.message);
    }
  };

  return (
    <div style={{ padding: '2rem' }}>
      <h2>Crear Receta Médica</h2>
      {mensaje && <p style={{ color: 'blue' }}>{mensaje}</p>}
      
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: '500px' }}>
        <label>
          ID del Paciente:
          <input type="text" value={pacienteId} onChange={(e) => setPacienteId(e.target.value)} required style={{ width: '100%' }} />
        </label>

        <h3>Medicamentos</h3>
        {medicamentos.map((med, index) => (
          <div key={index} style={{ border: '1px solid #ccc', padding: '1rem', borderRadius: '5px' }}>
            <input type="text" placeholder="Nombre del medicamento" value={med.nombre} onChange={(e) => handleMedChange(index, 'nombre', e.target.value)} required style={{ display: 'block', marginBottom: '0.5rem', width: '100%' }} />
            <input type="text" placeholder="Dosis (ej. 500mg)" value={med.dosis} onChange={(e) => handleMedChange(index, 'dosis', e.target.value)} required style={{ display: 'block', marginBottom: '0.5rem', width: '100%' }} />
            <input type="text" placeholder="Horario (ej. Cada 8 horas)" value={med.horario_toma} onChange={(e) => handleMedChange(index, 'horario_toma', e.target.value)} required style={{ display: 'block', width: '100%' }} />
          </div>
        ))}
        
        <button type="button" onClick={agregarMedicamento}>+ Agregar otro medicamento</button>
        <button type="submit" style={{ background: 'var(--primary-color)', color: 'white' }}>Guardar Receta</button>
      </form>
    </div>
  );
}
