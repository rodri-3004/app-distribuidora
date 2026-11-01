// frontend/src/App.tsx
import { useState } from 'react';
import { loginUsuario } from './services/api';
import './App.css';

function App() {
  const [email, setEmail] = useState('');
  const [clave, setClave] = useState('');
  const [usuarioLogueado, setUsuarioLogueado] = useState<any>(null);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const data = await loginUsuario(email, clave);
      setUsuarioLogueado(data.usuario);
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '40px', maxWidth: '400px', margin: '0 auto' }}>
      <h2>B2B Distribuidora - Acceso</h2>
      
      {!usuarioLogueado ? (
        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '5px' }}>Email:</label>
            <input 
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              required 
              style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '5px' }}>Contraseña:</label>
            <input 
              type="password" 
              value={clave} 
              onChange={(e) => setClave(e.target.value)} 
              required 
              style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
            />
          </div>
          <button type="submit" style={{ padding: '10px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer' }}>
            Ingresar
          </button>
          {error && <p style={{ color: 'red' }}>{error}</p>}
        </form>
      ) : (
        <div style={{ background: '#f0fdf4', padding: '20px', border: '1px solid #bbf7d0', borderRadius: '5px' }}>
          <h3 style={{ color: '#166534' }}>¡Bienvenido, {usuarioLogueado.nombre}!</h3>
          <p><strong>Email:</strong> {usuarioLogueado.email}</p>
          <p><strong>Rol:</strong> {usuarioLogueado.rol}</p>
          <button 
            onClick={() => setUsuarioLogueado(null)} 
            style={{ padding: '8px 12px', background: '#dc2626', color: '#fff', border: 'none', cursor: 'pointer' }}
          >
            Cerrar Sesión
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
