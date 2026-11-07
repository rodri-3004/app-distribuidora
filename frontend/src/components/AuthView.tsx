import React, { useState, useEffect } from 'react';
import { Mail, Lock, ArrowRight, Sparkles, CheckCircle2, AlertCircle, KeyRound, ShieldCheck, Truck } from 'lucide-react';

const API_URL = 'http://localhost:8001';

interface AuthViewProps {
  onLoginSuccess: (usuario: any) => void;
}

export const AuthView: React.FC<AuthViewProps> = ({ onLoginSuccess }) => {
  const [mode, setMode] = useState<'login' | 'register' | 'forgot' | 'activate' | 'reset'>('login');
  
  // Estados de formularios
  const [email, setEmail] = useState('');
  const [clave, setClave] = useState('');
  const [confirmarClave, setConfirmarClave] = useState('');
  const [nombre, setNombre] = useState('');
  const [apellido, setApellido] = useState('');
  const [dniCuil, setDniCuil] = useState('');
  
  // Tokens y códigos
  const [tokenInput, setTokenInput] = useState('');
  const [nuevaClave, setNuevaClave] = useState('');
  const [confirmarNuevaClave, setConfirmarNuevaClave] = useState('');
  const [debugInfo, setDebugInfo] = useState('');

  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Limpia los mensajes de error/éxito al cambiar de modo
  useEffect(() => {
    setErrorMsg(null);
    setSuccessMsg(null);
  }, [mode]);

  // Función para limpiar campos de registro
  const limpiarFormularioRegistro = () => {
    setNombre('');
    setApellido('');
    setDniCuil('');
    setClave('');
    setConfirmarClave('');
  };

  // 1. Iniciar Sesión
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, clave })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Error al iniciar sesión');

      // Guardar token
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
      }

      onLoginSuccess(data.usuario);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 2. Registro de Usuario Nuevo
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    if (clave !== confirmarClave) {
      setErrorMsg('Las contraseñas no coinciden.');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/registro`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nombre,
          apellido,
          email,
          dni_cuil: dniCuil,
          clave,
          confirmar_clave: confirmarClave
        })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Error en el registro');

      setSuccessMsg(data.mensaje);
      if (data.token_debug) setDebugInfo(data.token_debug);
      
      limpiarFormularioRegistro();
      setMode('activate'); 
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 3. Activar Cuenta por Token
  const handleActivate = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/activar?email=${encodeURIComponent(email)}&token=${encodeURIComponent(tokenInput)}`, {
        method: 'POST'
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Error al activar cuenta');

      setSuccessMsg(data.mensaje);
      setTimeout(() => setMode('login'), 2000);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 4. Solicitar Recuperación de Contraseña
  const handleForgot = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/recuperar-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Error al solicitar recuperación');

      setSuccessMsg(data.mensaje);
      if (data.token_debug) setDebugInfo(data.token_debug);
      setMode('reset');
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  // 5. Restablecer Contraseña
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    if (nuevaClave !== confirmarNuevaClave) {
      setErrorMsg('Las nuevas contraseñas no coinciden.');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/resetear-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email,
          token: tokenInput,
          nueva_clave: nuevaClave,
          confirmar_nueva_clave: confirmarNuevaClave
        })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Error al restablecer contraseña');

      setSuccessMsg(data.mensaje);
      setNuevaClave('');
      setConfirmarNuevaClave('');
      setTokenInput('');
      setTimeout(() => setMode('login'), 2500);
    } catch (err: any) {
      setErrorMsg(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      position: 'relative',
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center', 
      padding: '20px',
      overflow: 'hidden'
    }}>
      {/* FONDO DE IMAGEN DIFUMINADO */}
       <div style={{
        position: 'absolute',
        inset: 0,
        backgroundImage: 'url("https://images.pexels.com/photos/4481326/pexels-photo-4481326.jpeg?auto=compress&cs=tinysrgb&w=1920")',
        backgroundSize: 'cover',
        backgroundPosition: 'center',
        filter: 'blur(8px) brightness(0.5) sepia(20%) hue-rotate(190deg) saturate(150%)',
        transform: 'scale(1.05)',
        zIndex: 0
      }}></div>

      {/* TARJETA DEL FORMULARIO */}
      <div style={{ 
        position: 'relative',
        zIndex: 1,
        width: '100%', 
        maxWidth: '640px', 
        background: 'rgba(255, 255, 255, 0.9)', // Blanco con un toque de transparencia
        backdropFilter: 'blur(10px)', // Efecto cristal
        borderRadius: '24px', 
        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.3)', 
        border: '1px solid rgba(255, 255, 255, 0.2)', 
        padding: '35px' 
      }}>
        
        {/* Encabezado */}
        <div style={{ textAlign: 'center', marginBottom: '25px' }}>
          <div style={{ background: '#3b82f6', width: '55px', height: '55px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '16px', margin: '0 auto 12px auto', boxShadow: '0 4px 10px rgba(59,130,246,0.3)' }}>
            <Truck size={32} color="#fff" />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginBottom: '4px' }}>
            <h2 style={{ margin: 0, fontSize: '24px', fontWeight: '800', color: '#0f172a', letterSpacing: '-0.5px' }}>DistriApp</h2>
            <span style={{ background: '#e2e8f0', color: '#475569', padding: '2px 6px', borderRadius: '6px', fontSize: '10px', fontWeight: 'bold' }}>PWA</span>
          </div>
          <p style={{ margin: 0, fontSize: '12px', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Preventa & Pedidos</p>
        </div>

        {/* Alertas */}
        {errorMsg && (
          <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', padding: '10px 14px', borderRadius: '10px', fontSize: '12px', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertCircle size={16} /> <span>{errorMsg}</span>
          </div>
        )}
        {successMsg && (
          <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534', padding: '10px 14px', borderRadius: '10px', fontSize: '12px', marginBottom: '15px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={16} /> <span>{successMsg}</span>
          </div>
        )}

        {/* MODO: LOGIN */}
        {mode === 'login' && (
          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Correo Electrónico</label>
              <div style={{ position: 'relative' }}>
                <Mail size={16} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '12px' }} />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="carlos@mail.com"
                  style={{ width: '100%', boxSizing: 'border-box', paddingLeft: '38px' }}
                />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Contraseña</label>
                <button type="button" onClick={() => setMode('forgot')} style={{ background: 'none', border: 'none', color: '#2563eb', fontSize: '11px', fontWeight: 'bold', cursor: 'pointer', padding: 0 }}>
                  ¿Olvidaste tu contraseña?
                </button>
              </div>
              <div style={{ position: 'relative' }}>
                <Lock size={16} color="#94a3b8" style={{ position: 'absolute', left: '12px', top: '12px' }} />
                <input
                  type="password"
                  required
                  value={clave}
                  onChange={(e) => setClave(e.target.value)}
                  placeholder="••••••••"
                  style={{ width: '100%', boxSizing: 'border-box', paddingLeft: '38px' }}
                />
              </div>
            </div>

            <button type="submit" disabled={loading} style={{ padding: '12px', background: 'linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%)', color: '#fff', border: 'none', borderRadius: '10px', fontWeight: 'bold', fontSize: '14px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginTop: '5px' }}>
              {loading ? 'Iniciando sesión...' : 'Iniciar Sesión'} <ArrowRight size={16} />
            </button>

            <div style={{ textAlign: 'center', marginTop: '15px', fontSize: '13px', color: '#64748b' }}>
              ¿No tienes cuenta?{' '}
              <button type="button" onClick={() => setMode('register')} style={{ background: 'none', border: 'none', color: '#2563eb', fontWeight: 'bold', cursor: 'pointer' }}>
                Registrarse
              </button>
            </div>
          </form>
        )}

        {/* MODO: REGISTRO */}
        {mode === 'register' && (
          <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Nombre</label>
                <input type="text" required value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Carlos" style={{ width: '100%', boxSizing: 'border-box' }} />
              </div>
              <div>
                <label style={{ display: 'block', marginBottom: '4px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Apellido</label>
                <input type="text" required value={apellido} onChange={(e) => setApellido(e.target.value)} placeholder="Gómez" style={{ width: '100%', boxSizing: 'border-box' }} />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Correo Electrónico</label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="carlos@mail.com" style={{ width: '100%', boxSizing: 'border-box' }} />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>DNI / CUIT / CUIL</label>
              <input type="text" required value={dniCuil} onChange={(e) => setDniCuil(e.target.value)} placeholder="20-33445566-1 ó 33445566" style={{ width: '100%', boxSizing: 'border-box' }} />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Contraseña Segura</label>
              <input type="password" required value={clave} onChange={(e) => setClave(e.target.value)} placeholder="Mínimo 8 caracteres (letras y números)" style={{ width: '100%', boxSizing: 'border-box' }} />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Confirmar Contraseña</label>
              <input type="password" required value={confirmarClave} onChange={(e) => setConfirmarClave(e.target.value)} placeholder="Repite tu contraseña" style={{ width: '100%', boxSizing: 'border-box' }} />
            </div>

            <button type="submit" disabled={loading} style={{ padding: '12px', background: 'linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%)', color: '#fff', border: 'none', borderRadius: '10px', fontWeight: 'bold', fontSize: '14px', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', marginTop: '5px' }}>
              {loading ? 'Registrando...' : 'Completar Registro'} <Sparkles size={16} color="#fde047" />
            </button>

            <div style={{ textAlign: 'center', marginTop: '10px', fontSize: '13px', color: '#64748b' }}>
              ¿Ya tienes cuenta?{' '}
              <button type="button" onClick={() => setMode('login')} style={{ background: 'none', border: 'none', color: '#2563eb', fontWeight: 'bold', cursor: 'pointer' }}>
                Iniciar Sesión
              </button>
            </div>
          </form>
        )}

        {/* MODO: ACTIVAR CUENTA POR CORREO */}
        {mode === 'activate' && (
          <form onSubmit={handleActivate} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <div style={{ textAlign: 'center', color: '#475569', fontSize: '13px' }}>
              <ShieldCheck size={40} color="#2563eb" style={{ marginBottom: '8px' }} />
              <p>Te hemos enviado un correo de activación a <strong>{email}</strong>.</p>
              {debugInfo && (
                <div style={{ background: '#f1f5f9', padding: '10px', borderRadius: '8px', marginTop: '10px', fontSize: '12px', border: '1px dashed #cbd5e1' }}>
                  🔑 <em>Código simulado (bandeja de entrada):</em><br/>
                  <strong style={{ fontSize: '16px', color: '#1e3a8a' }}>{debugInfo}</strong>
                </div>
              )}
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Ingresa el Token de Activación</label>
              <input type="text" required value={tokenInput} onChange={(e) => setTokenInput(e.target.value.toUpperCase())} placeholder="Ej. A1B2C3D4" style={{ width: '100%', boxSizing: 'border-box', textAlign: 'center', letterSpacing: '2px', fontWeight: 'bold' }} />
            </div>

            <button type="submit" disabled={loading} style={{ padding: '12px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: '10px', fontWeight: 'bold', fontSize: '14px', cursor: 'pointer' }}>
              {loading ? 'Verificando...' : 'Activar Cuenta'}
            </button>

            <div style={{ textAlign: 'center' }}>
              <button type="button" onClick={() => setMode('login')} style={{ background: 'none', border: 'none', color: '#2563eb', fontSize: '13px', fontWeight: 'bold', cursor: 'pointer' }}>
                ← Volver al login
              </button>
            </div>
          </form>
        )}

        {/* MODO: RECUPERAR CONTRASEÑA */}
        {mode === 'forgot' && (
          <form onSubmit={handleForgot} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
            <p style={{ fontSize: '13px', color: '#64748b', lineHeight: '1.5', margin: 0 }}>
              Ingresa tu correo electrónico registrado y te enviaremos un código para restablecer tu contraseña.
            </p>

            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Correo Electrónico</label>
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="carlos@mail.com" style={{ width: '100%', boxSizing: 'border-box' }} />
            </div>

            <button type="submit" disabled={loading} style={{ padding: '12px', background: '#1e3a8a', color: '#fff', border: 'none', borderRadius: '10px', fontWeight: 'bold', fontSize: '14px', cursor: 'pointer' }}>
              {loading ? 'Enviando...' : 'Enviar Código de Recuperación'}
            </button>

            <div style={{ textAlign: 'center' }}>
              <button type="button" onClick={() => setMode('login')} style={{ background: 'none', border: 'none', color: '#475569', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}>
                ← Volver al inicio de sesión
              </button>
            </div>
          </form>
        )}

        {/* MODO: RESETEAR CONTRASEÑA */}
        {mode === 'reset' && (
          <form onSubmit={handleResetPassword} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ textAlign: 'center', color: '#475569', fontSize: '13px', marginBottom: '5px' }}>
              <KeyRound size={32} color="#2563eb" style={{ marginBottom: '4px' }} />
              <p>Ingresa el código recibido y define tu nueva contraseña.</p>
              {debugInfo && (
                <div style={{ background: '#f1f5f9', padding: '8px', borderRadius: '6px', marginTop: '6px', fontSize: '12px', border: '1px dashed #cbd5e1' }}>
                  🔑 <em>Código debug:</em> <strong style={{ color: '#1e3a8a' }}>{debugInfo}</strong>
                </div>
              )}
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Código de Verificación</label>
              <input type="text" required value={tokenInput} onChange={(e) => setTokenInput(e.target.value.toUpperCase())} placeholder="Ej. A1B2C" style={{ width: '100%', boxSizing: 'border-box', textAlign: 'center', letterSpacing: '2px', fontWeight: 'bold' }} />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Nueva Contraseña Segura</label>
              <input type="password" required value={nuevaClave} onChange={(e) => setNuevaClave(e.target.value)} placeholder="Mínimo 8 caracteres (letras y números)" style={{ width: '100%', boxSizing: 'border-box' }} />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '4px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Confirmar Nueva Contraseña</label>
              <input type="password" required value={confirmarNuevaClave} onChange={(e) => setConfirmarNuevaClave(e.target.value)} placeholder="Repite tu nueva contraseña" style={{ width: '100%', boxSizing: 'border-box' }} />
            </div>

            <button type="submit" disabled={loading} style={{ padding: '12px', background: '#16a34a', color: '#fff', border: 'none', borderRadius: '10px', fontWeight: 'bold', fontSize: '14px', cursor: 'pointer', marginTop: '5px' }}>
              {loading ? 'Actualizando...' : 'Actualizar Contraseña'}
            </button>

            <div style={{ textAlign: 'center' }}>
              <button type="button" onClick={() => setMode('login')} style={{ background: 'none', border: 'none', color: '#475569', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}>
                ← Volver al login
              </button>
            </div>
          </form>
        )}

      </div>
    </div>
  );
};