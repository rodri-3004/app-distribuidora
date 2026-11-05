import { useState, useEffect, useRef } from 'react';
import { obtenerProductos } from './services/api';
import { AuthView } from './components/AuthView';
import { Key, LogOut, ChevronDown, X, AlertCircle, CheckCircle2, Menu } from 'lucide-react';
import './App.css';

const API_URL = 'http://localhost:8001';

// ==========================================
// COMPONENTE: MENÚ DESPLEGABLE DE USUARIO (NAVBAR)
// ==========================================
function UserMenuDropdown({ usuario, onOpenChangePassword, onLogout }: { usuario: any; onOpenChangePassword: () => void; onLogout: () => void }) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div style={{ position: 'relative', display: 'inline-block' }} ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        style={{ background: '#1d4ed8', border: 'none', color: '#fff', padding: '9px 14px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: '600', cursor: 'pointer', boxShadow: '0 2px 4px rgba(29,78,216,0.2)', whiteSpace: 'nowrap' }}
      >
        <div style={{ width: '22px', height: '22px', borderRadius: '6px', background: '#1e40af', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '11px', fontWeight: 'bold' }}>
          {usuario?.nombre ? usuario.nombre.charAt(0).toUpperCase() : 'U'}
        </div>
        <span>{usuario?.nombre || 'Usuario'}</span>
        <ChevronDown size={14} style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }} />
      </button>

      {isOpen && (
        <div style={{ position: 'absolute', right: 0, marginTop: '10px', width: '220px', background: '#fff', borderRadius: '16px', boxShadow: '0 15px 30px rgba(0,0,0,0.15)', border: '1px solid #e2e8f0', padding: '8px 0', zIndex: 1100, color: '#334155', fontSize: '13px' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #f1f5f9', background: '#f8fafc' }}>
            <p style={{ margin: 0, fontWeight: 'bold', color: '#0f172a' }}>{usuario?.nombre} {usuario?.apellido}</p>
            <p style={{ margin: '2px 0 0 0', fontSize: '11px', color: '#64748b', textOverflow: 'ellipsis', overflow: 'hidden' }}>{usuario?.email}</p>
          </div>

          <button
            onClick={() => { setIsOpen(false); onOpenChangePassword(); }}
            style={{ width: '100%', textAlign: 'left', padding: '11px 16px', background: 'none', border: 'none', display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', color: '#475569', fontWeight: '500' }}
          >
            <Key size={15} color="#2563eb" /> Cambiar Contraseña
          </button>

          <div style={{ borderTop: '1px solid #f1f5f9', margin: '4px 0' }}></div>

          <button
            onClick={() => { setIsOpen(false); onLogout(); }}
            style={{ width: '100%', textAlign: 'left', padding: '11px 16px', background: 'none', border: 'none', display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', color: '#dc2626', fontWeight: '500' }}
          >
            <LogOut size={15} /> Cerrar Sesión
          </button>
        </div>
      )}
    </div>
  );
}

// ==========================================
// COMPONENTE: MODAL DE CAMBIO DE CONTRASEÑA
// ==========================================
function ChangePasswordModal({ isOpen, onClose, usuarioId }: { isOpen: boolean; onClose: () => void; usuarioId: number }) {
  const [actualPassword, setActualPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const passwordRules = {
    minLength: newPassword.length >= 8,
    hasUppercase: /[A-Z]/.test(newPassword),
    hasNumber: /\d/.test(newPassword),
    match: newPassword !== '' && newPassword === confirmPassword,
    isAllRulesMet: newPassword.length >= 8 && /[A-Z]/.test(newPassword) && /\d/.test(newPassword) && newPassword === confirmPassword
  };

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!actualPassword || !newPassword || !confirmPassword) {
      setError('Por favor, completa todos los campos.');
      return;
    }

    if (!passwordRules.isAllRulesMet) {
      setError('La nueva contraseña no cumple con los requisitos de seguridad o no coincide.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/cambiar-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          usuario_id: usuarioId,
          clave_actual: actualPassword,
          nueva_clave: newPassword,
          confirmar_nueva_clave: confirmPassword
        })
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Error al actualizar contraseña');

      setSuccess(true);
      setTimeout(() => {
        setSuccess(false);
        setActualPassword('');
        setNewPassword('');
        setConfirmPassword('');
        onClose();
      }, 2000);
    } catch (err: any) {
      setError(err.message || 'Error al actualizar la contraseña.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000, padding: '20px' }}>
      <div style={{ background: '#fff', borderRadius: '24px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)', maxWidth: '420px', width: '100%', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
        <div style={{ background: 'linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 100%)', padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#fff' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Key size={18} />
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 'bold' }}>Cambiar Contraseña</h3>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', opacity: 0.8 }}><X size={18} /></button>
        </div>

        <div style={{ padding: '28px' }}>
          {success ? (
            <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '16px', padding: '24px', textAlign: 'center', color: '#166534' }}>
              <CheckCircle2 size={40} color="#16a34a" style={{ margin: '0 auto 10px auto' }} />
              <p style={{ margin: 0, fontWeight: 'bold', fontSize: '15px' }}>¡Contraseña actualizada con éxito!</p>
            </div>
          ) : (
            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {error && (
                <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', padding: '12px 14px', borderRadius: '12px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <AlertCircle size={16} /> <span>{error}</span>
                </div>
              )}

              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: '#475569', marginBottom: '6px', textTransform: 'uppercase' }}>Contraseña Actual *</label>
                <input type="password" value={actualPassword} onChange={(e) => setActualPassword(e.target.value)} required style={{ width: '100%', padding: '10px 14px', borderRadius: '12px', border: '1px solid #cbd5e1', boxSizing: 'border-box', fontSize: '13px', background: '#f8fafc' }} placeholder="••••••••" />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: '#475569', marginBottom: '6px', textTransform: 'uppercase' }}>Nueva Contraseña Segura *</label>
                <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required style={{ width: '100%', padding: '10px 14px', borderRadius: '12px', border: '1px solid #cbd5e1', boxSizing: 'border-box', fontSize: '13px', background: '#f8fafc' }} placeholder="Mínimo 8 caracteres" />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Repetir Nueva Contraseña *</label>
                <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required style={{ width: '100%', padding: '10px 14px', borderRadius: '12px', border: '1px solid #cbd5e1', boxSizing: 'border-box', fontSize: '13px', background: '#f8fafc' }} placeholder="Repite tu nueva contraseña" />
              </div>

              <div style={{ background: '#f8fafc', padding: '14px', borderRadius: '12px', border: '1px solid #e2e8f0', fontSize: '11px', color: '#64748b', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <p style={{ margin: '0 0 2px 0', fontWeight: 'bold', color: '#334155' }}>Requisitos de seguridad:</p>
                <div style={{ color: passwordRules.minLength ? '#16a34a' : '#64748b' }}>{passwordRules.minLength ? '✓' : '•'} Mínimo 8 caracteres</div>
                <div style={{ color: passwordRules.hasUppercase ? '#16a34a' : '#64748b' }}>{passwordRules.hasUppercase ? '✓' : '•'} Una letra mayúscula y un número</div>
                <div style={{ color: passwordRules.match ? '#16a34a' : '#64748b' }}>{passwordRules.match ? '✓' : '•'} Las contraseñas coinciden</div>
              </div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                <button type="button" onClick={onClose} style={{ flex: 1, padding: '12px', background: '#f1f5f9', color: '#334155', border: 'none', borderRadius: '12px', fontWeight: 'bold', fontSize: '13px', cursor: 'pointer' }}>Cancelar</button>
                <button type="submit" disabled={loading || !passwordRules.isAllRulesMet} style={{ flex: 1, padding: '12px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '12px', fontWeight: 'bold', fontSize: '13px', cursor: 'pointer', opacity: (!passwordRules.isAllRulesMet || loading) ? 0.6 : 1 }}>{loading ? 'Guardando...' : 'Actualizar Clave'}</button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

// ==========================================
// COMPONENTE PRINCIPAL APP
// ==========================================
export default function App() {
  const [usuarioLogueado, setUsuarioLogueado] = useState<any>(null);
  const [isChangePasswordOpen, setIsChangePasswordOpen] = useState(false);
  
  const [productos, setProductos] = useState<any[]>([]);
  const [clientes, setClientes] = useState<any[]>([]);
  const [pedidos, setPedidos] = useState<any[]>([]);
  
  const [categoriaSeleccionada, setCategoriaSeleccionada] = useState<string>('Todas');
  const [busqueda, setBusqueda] = useState<string>('');
  const [cargandoProductos, setCargandoProductos] = useState(false);

  const [cantidadesTemp, setCantidadesTemp] = useState<{ [key: number]: number }>({});
  const [carrito, setCarrito] = useState<{ [key: number]: number }>({});
  const [observaciones, setObservaciones] = useState('');
  const [mensajePedido, setMensajePedido] = useState('');
  const [vistaActual, setVistaActual] = useState<'catalogo' | 'clientes' | 'historial'>('catalogo');
  const [carritoAbierto, setCarritoAbierto] = useState(false);
  const [menuMovilAbierto, setMenuMovilAbierto] = useState(false);

  const [clienteSeleccionadoId, setClienteSeleccionadoId] = useState<string>('');
  const [razonSocial, setRazonSocial] = useState('');
  const [cuit, setCuit] = useState('');
  const [direccion, setDireccion] = useState('');
  const [condicionFiscal, setCondicionFiscal] = useState('Responsable Inscripto');
  const [medioPago, setMedioPago] = useState('Efectivo contra entrega');
  const [telefono, setTelefono] = useState('');

  const [modoCliente, setModoCliente] = useState<'lista' | 'crear' | 'editar'>('lista');
  const [clienteEditandoId, setClienteEditandoId] = useState<number | null>(null);

  useEffect(() => {
    if (usuarioLogueado) {
      cargarDatosIniciales();
    }
  }, [usuarioLogueado]);

  const cargarDatosIniciales = async () => {
    setCargandoProductos(true);
    try {
      const prods = await obtenerProductos();
      setProductos(prods);

      const resClientes = await fetch(`${API_URL}/clientes`);
      const dataClientes = await resClientes.json();
      setClientes(dataClientes);

      const resPedidos = await fetch(`${API_URL}/pedidos/todos`);
      const dataPedidos = await resPedidos.json();
      setPedidos(dataPedidos);
    } catch (err) {
      console.error(err);
    } finally {
      setCargandoProductos(false);
    }
  };

  const cambiarCantidadTemp = (productoId: number, delta: number) => {
    const prod = productos.find(p => p.id === productoId);
    if (!prod) return;

    const actual = cantidadesTemp[productoId] || 0;
    const nueva = actual + delta;

    if (nueva < 0) return;
    if (nueva > prod.stock_fisico) {
      alert("No hay suficiente stock físico disponible.");
      return;
    }

    setCantidadesTemp({ ...cantidadesTemp, [productoId]: nueva });
  };

  const agregarAlCarritoDesdeCatalogo = (productoId: number) => {
    const cantidadSeleccionada = cantidadesTemp[productoId] || 0;
    if (cantidadSeleccionada <= 0) {
      alert("Selecciona al menos 1 unidad para agregar.");
      return;
    }

    const prod = productos.find(p => p.id === productoId);
    if (!prod || prod.stock_fisico < cantidadSeleccionada) {
      alert("Stock insuficiente.");
      return;
    }

    setProductos(productos.map(p => {
      if (p.id === productoId) {
        return { ...p, stock_fisico: p.stock_fisico - cantidadSeleccionada };
      }
      return p;
    }));

    const carritoActual = carrito[productoId] || 0;
    setCarrito({ ...carrito, [productoId]: carritoActual + cantidadSeleccionada });
    setCantidadesTemp({ ...cantidadesTemp, [productoId]: 0 });
    setCarritoAbierto(true);
  };

  const ajustarCantidadCarrito = (productoId: number, nuevaCant: number) => {
    const prodOriginal = productos.find(p => p.id === productoId);
    if (!prodOriginal) return;

    const cantActualEnCarrito = carrito[productoId] || 0;
    const diferencia = nuevaCant - cantActualEnCarrito;

    if (diferencia > 0 && prodOriginal.stock_fisico < diferencia) {
      alert("Stock insuficiente en depósito.");
      return;
    }

    setProductos(productos.map(p => {
      if (p.id === productoId) {
        return { ...p, stock_fisico: p.stock_fisico - diferencia };
      }
      return p;
    }));

    if (nuevaCant <= 0) {
      eliminarDelCarrito(productoId);
    } else {
      setCarrito({ ...carrito, [productoId]: nuevaCant });
    }
  };

  const eliminarDelCarrito = (productoId: number) => {
    const cantEnCarrito = carrito[productoId] || 0;
    setProductos(productos.map(p => {
      if (p.id === productoId) {
        return { ...p, stock_fisico: p.stock_fisico + cantEnCarrito };
      }
      return p;
    }));
    const nuevoCarrito = { ...carrito };
    delete nuevoCarrito[productoId];
    setCarrito(nuevoCarrito);
  };

  const seleccionarClienteExistente = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const id = e.target.value;
    setClienteSeleccionadoId(id);
    if (!id) {
      setRazonSocial(''); setCuit(''); setDireccion(''); setTelefono('');
      return;
    }
    const cli = clientes.find(c => c.id === Number(id));
    if (cli) {
      setRazonSocial(cli.razon_social);
      setCuit(cli.cuit);
      setDireccion(cli.direccion);
      setCondicionFiscal(cli.condicion_fiscal);
      setMedioPago(cli.medio_pago);
      setTelefono(cli.telefono);
    }
  };

  const guardarClienteManual = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!razonSocial || !cuit || !direccion) {
      alert("Complete los campos obligatorios.");
      return;
    }

    const payload = { razon_social: razonSocial, cuit, direccion, condicion_fiscal: condicionFiscal, medio_pago: medioPago, telefono };

    try {
      if (modoCliente === 'editar' && clienteEditandoId) {
        await fetch(`${API_URL}/clientes/${clienteEditandoId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        await fetch(`${API_URL}/clientes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      }
      await cargarDatosIniciales();
      setModoCliente('lista');
      setClienteEditandoId(null);
      setRazonSocial(''); setCuit(''); setDireccion(''); setTelefono('');
    } catch (err) {
      alert("Error al guardar cliente.");
    }
  };

  const eliminarClienteDirecto = async (id: number) => {
    if (!confirm("¿Desea eliminar este cliente?")) return;
    await fetch(`${API_URL}/clientes/${id}`, { method: 'DELETE' });
    cargarDatosIniciales();
  };

  const enviarPedido = async () => {
    setMensajePedido('');
    const items = Object.entries(carrito).map(([idStr, cantidad]) => ({
      producto_id: Number(idStr),
      cantidad: Number(cantidad)
    }));

    if (items.length === 0) {
      alert("El carrito está vacío.");
      return;
    }
    if (!razonSocial || !cuit || !direccion) {
      alert("Complete los datos del cliente.");
      return;
    }

    try {
      const bodyData = clienteSeleccionadoId ? {
        cliente_id: Number(clienteSeleccionadoId),
        observaciones_agente: observaciones,
        items: items
      } : {
        datos_cliente: { razon_social: razonSocial, cuit, direccion, condicion_fiscal: condicionFiscal, medio_pago: medioPago, telefono },
        observaciones_agente: observaciones,
        items: items
      };

      const response = await fetch(`${API_URL}/pedidos`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bodyData)
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Error al procesar pedido.");

      setMensajePedido(`¡Orden #${data.pedido_id} generada con éxito!`);
      setTimeout(() => {
        setMensajePedido('');
      }, 2000);

      setCarrito({});
      setCantidadesTemp({});
      setObservaciones('');
      setCarritoAbierto(false);
      cargarDatosIniciales();
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    }
  };

  const calcularTotal = () => {
    let total = 0;
    for (const [idStr, cantidad] of Object.entries(carrito)) {
      const prod = productos.find(p => p.id === Number(idStr));
      if (prod) total += prod.precio * cantidad;
    }
    return total;
  };

  const cantidadTotalItems = () => Object.values(carrito).reduce((a, b) => a + b, 0);

  const productosFiltrados = productos.filter(p => {
    const coincideCat = categoriaSeleccionada === 'Todas' || (p.categoria && p.categoria.toLowerCase() === categoriaSeleccionada.toLowerCase());
    const coincideBusq = p.nombre.toLowerCase().includes(busqueda.toLowerCase()) || (p.codigo && p.codigo.toLowerCase().includes(busqueda.toLowerCase()));
    return coincideCat && coincideBusq;
  });

  if (!usuarioLogueado) {
    return <AuthView onLoginSuccess={(u) => setUsuarioLogueado(u)} />;
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', paddingBottom: '60px', fontFamily: 'system-ui, sans-serif', width: '100%', boxSizing: 'border-box' }}>
      
      {/* NAVBAR RESPONSIVO Y FLUIDO */}
      <header style={{ background: 'linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 100%)', color: '#ffffff', padding: '16px 24px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '12px', boxShadow: '0 4px 20px rgba(30, 58, 138, 0.15)', position: 'sticky', top: 0, zIndex: 1000, width: '100%', boxSizing: 'border-box' }}>
        
        {/* Logo y Botón Menú Móvil */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button 
            onClick={() => setMenuMovilAbierto(!menuMovilAbierto)} 
            style={{ display: 'none', background: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff', padding: '8px', borderRadius: '10px', cursor: 'pointer' }}
            className="mobile-menu-btn"
          >
            <Menu size={22} />
          </button>
          
          <div onClick={() => setVistaActual('catalogo')} style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
            <div style={{ background: '#3b82f6', width: '38px', height: '38px', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px', boxShadow: '0 2px 6px rgba(0,0,0,0.1)' }}>📦</div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <h2 style={{ margin: '0', fontSize: '17px', fontWeight: '800', color: '#fff' }}>DistriApp</h2>
                <span style={{ background: 'rgba(255,255,255,0.2)', padding: '1px 5px', borderRadius: '5px', fontSize: '9px', fontWeight: 'bold' }}>PWA</span>
              </div>
              <p style={{ margin: '0', fontSize: '9px', opacity: 0.8, textTransform: 'uppercase' }}>Preventa & Pedidos</p>
            </div>
          </div>
        </div>

        {/* Botones de Navegación Centrales (Escritorio) */}
        <div style={{ display: 'flex', gap: '6px', background: 'rgba(0,0,0,0.15)', padding: '4px', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.1)' }} className="desktop-nav">
          <button onClick={() => setVistaActual('catalogo')} style={{ background: vistaActual === 'catalogo' ? '#2563eb' : 'transparent', color: '#fff', border: 'none', padding: '8px 14px', borderRadius: '10px', fontSize: '12px', fontWeight: '600', cursor: 'pointer', whiteSpace: 'nowrap' }}>📦 Catálogo & Pedidos</button>
          <button onClick={() => setVistaActual('clientes')} style={{ background: vistaActual === 'clientes' ? '#2563eb' : 'transparent', color: '#fff', border: 'none', padding: '8px 14px', borderRadius: '10px', fontSize: '12px', fontWeight: '600', cursor: 'pointer', whiteSpace: 'nowrap' }}>👥 Mis Clientes</button>
          <button onClick={() => setVistaActual('historial')} style={{ background: vistaActual === 'historial' ? '#2563eb' : 'transparent', color: '#fff', border: 'none', padding: '8px 14px', borderRadius: '10px', fontSize: '12px', fontWeight: '600', cursor: 'pointer', whiteSpace: 'nowrap' }}>📋 Historial de Pedidos</button>
        </div>

        {/* Acciones de Derecha (Carrito y Usuario) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginLeft: 'auto' }}>
          <button onClick={() => setCarritoAbierto(true)} style={{ background: '#2563eb', border: 'none', color: '#fff', fontSize: '12px', padding: '8px 14px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 'bold', cursor: 'pointer', boxShadow: '0 4px 12px rgba(37,99,235,0.3)', whiteSpace: 'nowrap' }}>
            🛒 Carrito {cantidadTotalItems() > 0 && <span style={{ background: '#10b981', color: '#fff', fontSize: '10px', padding: '1px 6px', borderRadius: '50px' }}>{cantidadTotalItems()}</span>}
          </button>
          
          <UserMenuDropdown 
            usuario={usuarioLogueado} 
            onOpenChangePassword={() => setIsChangePasswordOpen(true)} 
            onLogout={() => setUsuarioLogueado(null)} 
          />
        </div>

        {/* Menú Desplegable Móvil con Animación Suave */}
        {menuMovilAbierto && (
          <div className="mobile-dropdown-menu" style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '6px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.15)' }}>
            <button onClick={() => { setVistaActual('catalogo'); setMenuMovilAbierto(false); }} style={{ background: vistaActual === 'catalogo' ? '#2563eb' : 'rgba(255,255,255,0.05)', color: '#fff', border: 'none', padding: '10px 14px', borderRadius: '10px', fontSize: '13px', fontWeight: '600', textAlign: 'left', cursor: 'pointer' }}>📦 Catálogo & Pedidos</button>
            <button onClick={() => { setVistaActual('clientes'); setMenuMovilAbierto(false); }} style={{ background: vistaActual === 'clientes' ? '#2563eb' : 'rgba(255,255,255,0.05)', color: '#fff', border: 'none', padding: '10px 14px', borderRadius: '10px', fontSize: '13px', fontWeight: '600', textAlign: 'left', cursor: 'pointer' }}>👥 Mis Clientes</button>
            <button onClick={() => { setVistaActual('historial'); setMenuMovilAbierto(false); }} style={{ background: vistaActual === 'historial' ? '#2563eb' : 'rgba(255,255,255,0.05)', color: '#fff', border: 'none', padding: '10px 14px', borderRadius: '10px', fontSize: '13px', fontWeight: '600', textAlign: 'left', cursor: 'pointer' }}>📋 Historial de Pedidos</button>
          </div>
        )}
      </header>

      {/* Estilos CSS para animaciones fluidas y diseño responsivo */}
      <style>{`
        @keyframes slideDown {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes slideInRight {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        .mobile-dropdown-menu {
          animation: slideDown 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        .cart-backdrop {
          animation: fadeIn 0.25s ease-out forwards;
        }
        .cart-drawer {
          animation: slideInRight 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }
        @media (max-width: 900px) {
          .desktop-nav { display: none !important; }
          .mobile-menu-btn { display: flex !important; }
        }
      `}</style>

      {/* MODAL CAMBIO DE CONTRASEÑA */}
      <ChangePasswordModal 
        isOpen={isChangePasswordOpen} 
        onClose={() => setIsChangePasswordOpen(false)} 
        usuarioId={usuarioLogueado?.id || 1} 
      />

      {/* CONTENEDOR PRINCIPAL FLUIDO A ANCHO COMPLETO */}
      <main style={{ width: '100%', padding: '30px 35px', boxSizing: 'border-box' }}>
        {mensajePedido && <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '16px 20px', borderRadius: '14px', marginBottom: '30px', color: '#166534', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.02)' }}><CheckCircle2 size={20} color="#16a34a" />{mensajePedido}</div>}

        {/* VISTA 1: CATÁLOGO */}
        {vistaActual === 'catalogo' && (
          <div>
            <div style={{ background: '#fff', padding: '26px 30px', borderRadius: '20px', border: '1px solid #e2e8f0', marginBottom: '25px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '15px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.02)' }}>
              <div>
                <h2 style={{ color: '#0f172a', margin: '0 0 6px 0', fontSize: '24px', fontWeight: '800', letterSpacing: '-0.5px' }}>Catálogo de Productos</h2>
                <p style={{ margin: '0', fontSize: '13px', color: '#64748b' }}>Selecciona los bultos y presiona "Agregar" para incorporarlos al pedido.</p>
              </div>
              <input type="text" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} placeholder="Buscar por nombre o SKU..." style={{ width: '320px', maxWidth: '100%', padding: '11px 16px', borderRadius: '14px', border: '1px solid #cbd5e1', fontSize: '13px', outline: 'none', background: '#f8fafc' }} />
            </div>

            <div style={{ display: 'flex', gap: '10px', marginBottom: '25px', overflowX: 'auto', paddingBottom: '5px' }}>
              {['Todas', 'Bebidas y Jugos', 'Almacén y Comestibles', 'Snacks y Golosinas', 'Limpieza y Perfumería', 'Lácteos y Fríos'].map(cat => (
                <button key={cat} onClick={() => setCategoriaSeleccionada(cat)} style={{ padding: '10px 18px', borderRadius: '24px', border: '1px solid #cbd5e1', background: categoriaSeleccionada === cat ? '#1e3a8a' : '#fff', color: categoriaSeleccionada === cat ? '#fff' : '#475569', fontSize: '13px', fontWeight: '600', cursor: 'pointer', whiteSpace: 'nowrap', boxShadow: '0 2px 4px rgba(0,0,0,0.02)', transition: 'all 0.2s' }}>{cat}</button>
              ))}
            </div>

            {cargandoProductos ? <p style={{ textAlign: 'center', padding: '60px', color: '#64748b', fontSize: '15px' }}>Cargando productos del sistema...</p> : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
                {productosFiltrados.map(prod => {
                  const cantTemp = cantidadesTemp[prod.id] || 0;
                  return (
                    <div key={prod.id} style={{ background: '#fff', borderRadius: '20px', overflow: 'hidden', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '20px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.03)', transition: 'transform 0.2s, box-shadow 0.2s' }}>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                          <span style={{ background: '#eff6ff', color: '#1e3a8a', border: '1px solid #dbeafe', padding: '3px 9px', borderRadius: '8px', fontSize: '11px', fontWeight: 'bold' }}>{prod.codigo}</span>
                          <span style={{ background: prod.stock_fisico > 0 ? '#f0fdf4' : '#fef2f2', color: prod.stock_fisico > 0 ? '#16a34a' : '#dc2626', border: `1px solid ${prod.stock_fisico > 0 ? '#bbf7d0' : '#fecaca'}`, padding: '3px 9px', borderRadius: '8px', fontSize: '11px', fontWeight: 'bold' }}>Stock: {prod.stock_fisico}</span>
                        </div>
                        <h4 style={{ margin: '8px 0 10px 0', fontSize: '15px', color: '#0f172a', fontWeight: '700', lineHeight: '1.4' }}>{prod.nombre}</h4>
                        <p style={{ fontSize: '20px', fontWeight: '800', color: '#1e3a8a', margin: '0 0 10px 0' }}>${prod.precio.toLocaleString('es-AR')}</p>
                      </div>

                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '14px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', border: '1px solid #cbd5e1', borderRadius: '12px', background: '#f8fafc', overflow: 'hidden' }}>
                          <button onClick={() => cambiarCantidadTemp(prod.id, -1)} style={{ background: 'none', border: 'none', padding: '9px 12px', cursor: 'pointer', fontWeight: 'bold', color: '#475569' }}>-</button>
                          <span style={{ padding: '0 6px', fontSize: '13px', fontWeight: 'bold', color: '#0f172a' }}>{cantTemp}</span>
                          <button onClick={() => cambiarCantidadTemp(prod.id, 1)} style={{ background: 'none', border: 'none', padding: '9px 12px', cursor: 'pointer', fontWeight: 'bold', color: '#475569' }}>+</button>
                        </div>
                        <button onClick={() => agregarAlCarritoDesdeCatalogo(prod.id)} style={{ flex: 1, background: '#2563eb', color: '#fff', border: 'none', borderRadius: '12px', padding: '11px', fontSize: '13px', fontWeight: 'bold', cursor: 'pointer', boxShadow: '0 4px 10px rgba(37,99,235,0.2)' }}>🛒 Agregar</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* VISTA 2: MIS CLIENTES */}
        {vistaActual === 'clientes' && (
          <div>
            <div style={{ background: '#fff', padding: '26px 30px', borderRadius: '20px', border: '1px solid #e2e8f0', marginBottom: '25px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '15px' }}>
              <div>
                <h2 style={{ color: '#0f172a', margin: '0 0 4px 0', fontSize: '24px', fontWeight: '800' }}>Mis Clientes B2B</h2>
                <p style={{ margin: '0', fontSize: '13px', color: '#64748b' }}>Administración de cuentas comerciales y datos fiscales.</p>
              </div>
              {modoCliente === 'lista' && (
                <button onClick={() => { setModoCliente('crear'); setClienteEditandoId(null); setRazonSocial(''); setCuit(''); setDireccion(''); setTelefono(''); }} style={{ background: '#16a34a', color: '#fff', border: 'none', padding: '11px 22px', borderRadius: '12px', fontWeight: 'bold', cursor: 'pointer', boxShadow: '0 4px 10px rgba(22,163,74,0.2)' }}>+ Nuevo Cliente</button>
              )}
            </div>

            {modoCliente !== 'lista' ? (
              <div style={{ background: '#fff', padding: '30px', borderRadius: '20px', border: '1px solid #e2e8f0', maxWidth: '650px', margin: '0 auto', boxShadow: '0 10px 25px rgba(0,0,0,0.05)' }}>
                <h3 style={{ marginTop: 0, color: '#0f172a', fontSize: '18px', fontWeight: '700', marginBottom: '20px' }}>{modoCliente === 'crear' ? 'Registrar Nuevo Cliente' : 'Modificar Cliente'}</h3>
                <form onSubmit={guardarClienteManual} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Razón Social *</label>
                    <input type="text" value={razonSocial} onChange={(e) => setRazonSocial(e.target.value)} required style={{ width: '100%', padding: '11px 14px', borderRadius: '12px', border: '1px solid #cbd5e1', boxSizing: 'border-box', background: '#f8fafc', fontSize: '13px' }} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                    <div>
                      <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>CUIT / DNI *</label>
                      <input type="text" value={cuit} onChange={(e) => setCuit(e.target.value)} required style={{ width: '100%', padding: '11px 14px', borderRadius: '12px', border: '1px solid #cbd5e1', boxSizing: 'border-box', background: '#f8fafc', fontSize: '13px' }} />
                    </div>
                    <div>
                      <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Teléfono / WhatsApp</label>
                      <input type="text" value={telefono} onChange={(e) => setTelefono(e.target.value)} style={{ width: '100%', padding: '11px 14px', borderRadius: '12px', border: '1px solid #cbd5e1', boxSizing: 'border-box', background: '#f8fafc', fontSize: '13px' }} />
                    </div>
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Dirección de Entrega *</label>
                    <input type="text" value={direccion} onChange={(e) => setDireccion(e.target.value)} required style={{ width: '100%', padding: '11px 14px', borderRadius: '12px', border: '1px solid #cbd5e1', boxSizing: 'border-box', background: '#f8fafc', fontSize: '13px' }} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                    <div>
                      <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Condición Fiscal</label>
                      <select value={condicionFiscal} onChange={(e) => setCondicionFiscal(e.target.value)} style={{ width: '100%', padding: '11px 14px', borderRadius: '12px', border: '1px solid #cbd5e1', boxSizing: 'border-box', background: '#f8fafc', fontSize: '13px' }}>
                        <option>Responsable Inscripto</option>
                        <option>Monotributo</option>
                        <option>Consumidor Final</option>
                      </select>
                    </div>
                    <div>
                      <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Medio de Pago</label>
                      <select value={medioPago} onChange={(e) => setMedioPago(e.target.value)} style={{ width: '100%', padding: '11px 14px', borderRadius: '12px', border: '1px solid #cbd5e1', boxSizing: 'border-box', background: '#f8fafc', fontSize: '13px' }}>
                        <option>Efectivo contra entrega</option>
                        <option>Transferencia Bancaria</option>
                        <option>Cuenta Corriente 30 días</option>
                      </select>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '12px', marginTop: '10px' }}>
                    <button type="submit" style={{ flex: 1, padding: '13px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '12px', fontWeight: 'bold', cursor: 'pointer', boxShadow: '0 4px 10px rgba(37,99,235,0.2)' }}>Guardar Cliente</button>
                    <button type="button" onClick={() => setModoCliente('lista')} style={{ padding: '13px 22px', background: '#e2e8f0', color: '#334155', border: 'none', borderRadius: '12px', fontWeight: 'bold', cursor: 'pointer' }}>Cancelar</button>
                  </div>
                </form>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
                {clientes.map(cli => (
                  <div key={cli.id} style={{ background: '#fff', borderRadius: '20px', padding: '22px', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.02)' }}>
                    <div>
                      <h4 style={{ margin: '0 0 10px 0', color: '#1e3a8a', fontSize: '17px', fontWeight: '700' }}>{cli.razon_social}</h4>
                      <p style={{ margin: '5px 0', fontSize: '13px', color: '#475569' }}><strong>CUIT:</strong> {cli.cuit}</p>
                      <p style={{ margin: '5px 0', fontSize: '13px', color: '#475569' }}><strong>Dir:</strong> {cli.direccion || 'Sin dirección'}</p>
                      <p style={{ margin: '5px 0', fontSize: '13px', color: '#475569' }}><strong>Pago:</strong> {cli.medio_pago || 'Efectivo'}</p>
                    </div>
                    <div style={{ display: 'flex', gap: '10px', marginTop: '20px', borderTop: '1px solid #f1f5f9', paddingTop: '14px' }}>
                      <button onClick={() => { setModoCliente('editar'); setClienteEditandoId(cli.id); setRazonSocial(cli.razon_social); setCuit(cli.cuit); setDireccion(cli.direccion); setCondicionFiscal(cli.condicion_fiscal); setMedioPago(cli.medio_pago); setTelefono(cli.telefono); }} style={{ flex: 1, background: '#f8fafc', color: '#1e3a8a', border: '1px solid #e2e8f0', padding: '9px', borderRadius: '10px', fontWeight: 'bold', cursor: 'pointer', fontSize: '13px' }}>✏️ Modificar</button>
                      <button onClick={() => eliminarClienteDirecto(cli.id)} style={{ background: '#fef2f2', color: '#dc2626', border: '1px solid #fee2e2', padding: '9px 12px', borderRadius: '10px', fontWeight: 'bold', cursor: 'pointer', fontSize: '13px' }}>🗑️</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* VISTA 3: HISTORIAL DE PEDIDOS */}
        {vistaActual === 'historial' && (
          <div>
            <div style={{ background: '#fff', padding: '26px 30px', borderRadius: '20px', border: '1px solid #e2e8f0', marginBottom: '25px' }}>
              <h2 style={{ color: '#0f172a', margin: '0 0 4px 0', fontSize: '24px', fontWeight: '800' }}>Historial de Órdenes & PDFs</h2>
              <p style={{ margin: '0', fontSize: '13px', color: '#64748b' }}>Listado cronológico de pedidos generados en el sistema.</p>
            </div>

            {pedidos.length === 0 ? <p style={{ textAlign: 'center', padding: '60px', color: '#64748b' }}>No hay pedidos registrados.</p> : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {pedidos.map(ped => (
                  <div key={ped.id} style={{ background: '#fff', borderRadius: '16px', padding: '20px 26px', border: '1px solid #e2e8f0', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '15px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
                        <h4 style={{ margin: '0', color: '#1e3a8a', fontSize: '17px', fontWeight: '700' }}>Orden #{ped.id} - {ped.razon_social || 'Cliente General'}</h4>
                        <span style={{ background: '#eff6ff', color: '#1d4ed8', border: '1px solid #dbeafe', padding: '3px 9px', borderRadius: '6px', fontSize: '11px', fontWeight: 'bold' }}>{ped.estado}</span>
                      </div>
                      <p style={{ margin: '3px 0', fontSize: '13px', color: '#64748b' }}>📅 Fecha: {ped.fecha}</p>
                      <p style={{ margin: '3px 0', fontSize: '13px', color: '#475569' }}>📝 Obs: {ped.observaciones_agente || 'Ninguna'}</p>
                    </div>
                    <div style={{ textAlign: 'right', display: 'flex', alignItems: 'center', gap: '20px' }}>
                      <div>
                        <span style={{ fontSize: '11px', color: '#64748b', display: 'block' }}>Total</span>
                        <span style={{ fontSize: '19px', fontWeight: '800', color: '#1e3a8a' }}>${ped.total.toLocaleString('es-AR')}</span>
                      </div>
                      <a href={`http://localhost:8001/documentos_pedidos/orden_pedido_${ped.id}.pdf`} target="_blank" rel="noopener noreferrer" style={{ background: '#dc2626', color: '#fff', padding: '10px 18px', borderRadius: '12px', fontSize: '13px', fontWeight: 'bold', textDecoration: 'none', boxShadow: '0 4px 10px rgba(220,38,38,0.2)' }}>📄 Ver PDF</a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* PANEL LATERAL CARRITO CON ESTRUCTURA RIGIDA Y SCROLL INTERNO */}
      {carritoAbierto && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 2000, display: 'flex' }}>
          <div 
            onClick={() => setCarritoAbierto(false)} 
            className="cart-backdrop"
            style={{ position: 'absolute', inset: 0, background: 'rgba(15, 23, 42, 0.5)', backdropFilter: 'blur(3px)' }} 
          />

          <div className="cart-drawer" style={{ position: 'relative', marginLeft: 'auto', width: '480px', maxWidth: '100%', height: '100vh', maxHeight: '100vh', background: '#fff', boxShadow: '-15px 0 40px rgba(0,0,0,0.2)', display: 'flex', flexDirection: 'column', boxSizing: 'border-box', zIndex: 2010, overflow: 'hidden' }}>
            
            {/* Cabecera Fija */}
            <div style={{ background: 'linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 100%)', color: '#fff', padding: '20px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
              <h3 style={{ margin: '0', fontSize: '17px', fontWeight: '700' }}>Carrito de Compras & Cierre</h3>
              <button onClick={() => setCarritoAbierto(false)} style={{ background: 'none', border: 'none', color: '#fff', fontSize: '18px', cursor: 'pointer', opacity: 0.8 }}><X size={20} /></button>
            </div>

            {/* Zona Central con Scroll Interno Independiente */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', minHeight: 0 }}>
              <div>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '11px', color: '#64748b', textTransform: 'uppercase', fontWeight: '700', letterSpacing: '0.5px' }}>Artículos Seleccionados ({cantidadTotalItems()})</h4>
                {Object.keys(carrito).length === 0 ? <p style={{ color: '#64748b', fontSize: '13px', fontStyle: 'italic' }}>El carrito está vacío.</p> : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {Object.entries(carrito).map(([idStr, cant]) => {
                      const prod = productos.find(p => p.id === Number(idStr));
                      if (!prod) return null;
                      return (
                        <div key={idStr} style={{ background: '#f8fafc', padding: '12px 14px', borderRadius: '12px', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <strong style={{ fontSize: '13px', display: 'block', color: '#0f172a', fontWeight: '600' }}>{prod.nombre}</strong>
                            <span style={{ fontSize: '11px', color: '#64748b' }}>${prod.precio.toLocaleString('es-AR')} c/u</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <input type="number" min="1" value={cant} onChange={(e) => ajustarCantidadCarrito(prod.id, parseInt(e.target.value) || 0)} style={{ width: '46px', textAlign: 'center', padding: '5px', borderRadius: '8px', border: '1px solid #cbd5e1', fontSize: '13px', background: '#fff' }} />
                            <button onClick={() => eliminarDelCarrito(prod.id)} style={{ background: 'none', border: 'none', color: '#dc2626', cursor: 'pointer', fontSize: '15px' }} title="Eliminar">🗑️</button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div style={{ background: '#eff6ff', border: '1px solid #dbeafe', padding: '16px', borderRadius: '14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0 }}>
                <span style={{ fontSize: '14px', fontWeight: 'bold', color: '#1e3a8a' }}>Total Pedido:</span>
                <span style={{ fontSize: '20px', fontWeight: '800', color: '#1e3a8a' }}>${calcularTotal().toLocaleString('es-AR')}</span>
              </div>

              {/* Selector de Cliente */}
              <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '18px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '11px', color: '#1e3a8a', textTransform: 'uppercase', fontWeight: '700', letterSpacing: '0.5px' }}>🏢 Datos del Cliente</h4>
                
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ fontSize: '10px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '5px', textTransform: 'uppercase' }}>Seleccionar de "Mis Clientes"</label>
                  <select value={clienteSeleccionadoId} onChange={seleccionarClienteExistente} style={{ width: '100%', padding: '9px 12px', borderRadius: '10px', border: '1px solid #cbd5e1', background: '#f8fafc', fontSize: '13px' }}>
                    <option value="">-- Cargar manualmente o nuevo cliente --</option>
                    {clientes.map(c => <option key={c.id} value={c.id}>{c.razon_social} (CUIT: {c.cuit})</option>)}
                  </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div>
                    <label style={{ fontSize: '10px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>Razón Social / Nombre *</label>
                    <input type="text" value={razonSocial} onChange={(e) => setRazonSocial(e.target.value)} placeholder="Ej. Kiosco Belgrano" style={{ width: '100%', padding: '9px 12px', boxSizing: 'border-box', borderRadius: '10px', border: '1px solid #cbd5e1', background: '#f8fafc', fontSize: '13px' }} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <div>
                      <label style={{ fontSize: '10px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>CUIT / DNI *</label>
                      <input type="text" value={cuit} onChange={(e) => setCuit(e.target.value)} placeholder="Ej. 30-7123" style={{ width: '100%', padding: '9px 12px', boxSizing: 'border-box', borderRadius: '10px', border: '1px solid #cbd5e1', background: '#f8fafc', fontSize: '13px' }} />
                    </div>
                    <div>
                      <label style={{ fontSize: '10px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>Teléfono</label>
                      <input type="text" value={telefono} onChange={(e) => setTelefono(e.target.value)} placeholder="Ej. 115566" style={{ width: '100%', padding: '9px 12px', boxSizing: 'border-box', borderRadius: '10px', border: '1px solid #cbd5e1', background: '#f8fafc', fontSize: '13px' }} />
                    </div>
                  </div>
                  <div>
                    <label style={{ fontSize: '10px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>Dirección de Entrega *</label>
                    <input type="text" value={direccion} onChange={(e) => setDireccion(e.target.value)} placeholder="Ej. Av. San Martín 1420" style={{ width: '100%', padding: '9px 12px', boxSizing: 'border-box', borderRadius: '10px', border: '1px solid #cbd5e1', background: '#f8fafc', fontSize: '13px' }} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    <div>
                      <label style={{ fontSize: '10px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>Condición Fiscal</label>
                      <select value={condicionFiscal} onChange={(e) => setCondicionFiscal(e.target.value)} style={{ width: '100%', padding: '9px 12px', borderRadius: '10px', border: '1px solid #cbd5e1', background: '#f8fafc', fontSize: '13px' }}>
                        <option>Responsable Inscripto</option>
                        <option>Monotributo</option>
                        <option>Consumidor Final</option>
                      </select>
                    </div>
                    <div>
                      <label style={{ fontSize: '10px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '4px', textTransform: 'uppercase' }}>Medio de Pago</label>
                      <select value={medioPago} onChange={(e) => setMedioPago(e.target.value)} style={{ width: '100%', padding: '9px 12px', borderRadius: '10px', border: '1px solid #cbd5e1', background: '#f8fafc', fontSize: '13px' }}>
                        <option>Efectivo contra entrega</option>
                        <option>Transferencia Bancaria</option>
                        <option>Cuenta Corriente 30 días</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: '#475569', marginBottom: '6px', textTransform: 'uppercase' }}>Observaciones del Pedido (Opcional)</label>
                <textarea value={observaciones} onChange={(e) => setObservaciones(e.target.value)} placeholder="Horarios de descarga..." rows={2} style={{ width: '100%', padding: '11px', borderRadius: '12px', border: '1px solid #cbd5e1', boxSizing: 'border-box', background: '#f8fafc', fontSize: '13px' }} />
              </div>
            </div>

            {/* Pie Fijo con el Botón de Confirmación (Siempre visible) */}
            <div style={{ padding: '16px 24px', background: '#f8fafc', borderTop: '1px solid #e2e8f0', flexShrink: 0 }}>
              <button onClick={enviarPedido} style={{ width: '100%', padding: '13px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '14px', fontSize: '14px', fontWeight: 'bold', cursor: 'pointer', boxShadow: '0 4px 15px rgba(37,99,235,0.3)' }}>✅ Confirmar y Generar PDF</button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}