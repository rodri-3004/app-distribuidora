import { useState, useEffect, useRef } from 'react';
import { obtenerProductos } from './services/api';
import { AuthView } from './components/AuthView';
import { Key, LogOut, ChevronDown, X, AlertCircle, CheckCircle2, Menu, Truck, ShoppingCart } from 'lucide-react';
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
        style={{ background: 'rgba(255, 255, 255, 0.15)', border: '1px solid rgba(255,255,255,0.2)', color: '#fff', padding: '8px 16px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: '600', cursor: 'pointer', transition: 'all 0.2s' }}
      >
        <div style={{ width: '24px', height: '24px', borderRadius: '6px', background: '#3b82f6', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontSize: '12px', fontWeight: 'bold' }}>
          {usuario?.nombre ? usuario.nombre.charAt(0).toUpperCase() : 'U'}
        </div>
        <span>{usuario?.nombre || 'Usuario'}</span>
        <ChevronDown size={14} style={{ transform: isOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }} />
      </button>

      {isOpen && (
        <div className="animate-slide-down" style={{ position: 'absolute', right: 0, marginTop: '10px', width: '240px', background: '#ffffff', borderRadius: '16px', boxShadow: '0 10px 25px rgba(0,0,0,0.15)', border: '1px solid #e2e8f0', padding: '8px 0', zIndex: 1100 }}>
          <div style={{ padding: '16px', borderBottom: '1px solid #f1f5f9' }}>
            <p style={{ margin: 0, fontWeight: '700', color: '#0f172a', fontSize: '14px' }}>{usuario?.nombre} {usuario?.apellido}</p>
            <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#64748b', textOverflow: 'ellipsis', overflow: 'hidden' }}>{usuario?.email}</p>
          </div>

          <button
            onClick={() => { setIsOpen(false); onOpenChangePassword(); }}
            style={{ width: '100%', textAlign: 'left', padding: '12px 16px', background: 'none', border: 'none', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', color: '#334155', fontWeight: '500', fontSize: '14px' }}
          >
            <Key size={16} color="#2563eb" /> Cambiar Contraseña
          </button>

          <div style={{ borderTop: '1px solid #f1f5f9', margin: '4px 0' }}></div>

          <button
            onClick={() => { setIsOpen(false); onLogout(); }}
            style={{ width: '100%', textAlign: 'left', padding: '12px 16px', background: 'none', border: 'none', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', color: '#dc2626', fontWeight: '500', fontSize: '14px' }}
          >
            <LogOut size={16} /> Cerrar Sesión
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
      setError('La nueva contraseña no cumple con los requisitos o no coincide.');
      return;
    }

    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/cambiar-password`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
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
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000, padding: '20px' }}>
      <div className="animate-fade-in" style={{ background: '#fff', borderRadius: '24px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)', maxWidth: '420px', width: '100%', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
        <div style={{ background: '#1e3a8a', padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#fff' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Key size={18} />
            <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 'bold', color: '#fff' }}>Cambiar Contraseña</h3>
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
                <input type="password" value={actualPassword} onChange={(e) => setActualPassword(e.target.value)} required placeholder="••••••••" />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 'bold', color: '#475569', marginBottom: '6px', textTransform: 'uppercase' }}>Nueva Contraseña Segura *</label>
                <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required placeholder="Mínimo 8 caracteres" />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '6px', fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Repetir Nueva Contraseña *</label>
                <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required placeholder="Repite tu nueva contraseña" />
              </div>

              <div style={{ background: '#f8fafc', padding: '14px', borderRadius: '12px', border: '1px solid #e2e8f0', fontSize: '11px', color: '#64748b', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <p style={{ margin: '0 0 2px 0', fontWeight: 'bold', color: '#334155' }}>Requisitos de seguridad:</p>
                <div style={{ color: passwordRules.minLength ? '#16a34a' : '#64748b' }}>{passwordRules.minLength ? '✓' : '•'} Mínimo 8 caracteres</div>
                <div style={{ color: passwordRules.hasUppercase ? '#16a34a' : '#64748b' }}>{passwordRules.hasUppercase ? '✓' : '•'} Una letra mayúscula y un número</div>
                <div style={{ color: passwordRules.match ? '#16a34a' : '#64748b' }}>{passwordRules.match ? '✓' : '•'} Las contraseñas coinciden</div>
              </div>

              <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
                <button type="button" onClick={onClose} className="btn-secondary" style={{ flex: 1 }}>Cancelar</button>
                <button type="submit" disabled={loading || !passwordRules.isAllRulesMet} className="btn-primary" style={{ flex: 1, opacity: (!passwordRules.isAllRulesMet || loading) ? 0.6 : 1 }}>{loading ? 'Guardando...' : 'Actualizar Clave'}</button>
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
  const [fechaEntrega, setFechaEntrega] = useState<string>('');
  const [mensajePedido, setMensajePedido] = useState('');
  const [vistaActual, setVistaActual] = useState<'catalogo' | 'clientes' | 'historial'>('catalogo');
  const [carritoAbierto, setCarritoAbierto] = useState(false);
  const [menuMovilAbierto, setMenuMovilAbierto] = useState(false);

  const [modalSeguimientoAbierto, setModalSeguimientoAbierto] = useState(false);
  const [pedidoSeleccionado, setPedidoSeleccionado] = useState<any>(null);
  const [lineaTiempo, setLineaTiempo] = useState<any[]>([]);

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

  // POLLING PARA AVISO DE CAMBIO DE ESTADO (M2)
  useEffect(() => {
    if (!usuarioLogueado) return;
    const interval = setInterval(async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${API_URL}/pedidos/todos`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) {
          const nuevosPedidos = await res.json();
          nuevosPedidos.forEach((nuevo: any) => {
            const viejo = pedidos.find((p: any) => p.id === nuevo.id);
            if (viejo && viejo.estado !== nuevo.estado) {
              setMensajePedido(`El pedido #${nuevo.id} cambió a: ${nuevo.estado_cliente}`);
              setTimeout(() => setMensajePedido(''), 5000);
            }
          });
          setPedidos(nuevosPedidos);
        }
      } catch (err) { console.error("Error en polling:", err); }
    }, 15000);
    return () => clearInterval(interval);
  }, [usuarioLogueado, pedidos]);

  const cargarDatosIniciales = async () => {
    setCargandoProductos(true);
    try {
      const prods = await obtenerProductos();
      setProductos(prods);

      const token = localStorage.getItem('token');
      const headers = { 'Authorization': `Bearer ${token}` };

      const resClientes = await fetch(`${API_URL}/clientes`, { headers });
      if (resClientes.status === 401) { handleLogout(); return; }
      const dataClientes = await resClientes.json();
      setClientes(dataClientes);

      const resPedidos = await fetch(`${API_URL}/pedidos/todos`, { headers });
      if (resPedidos.status === 401) { handleLogout(); return; }
      const dataPedidos = await resPedidos.json();
      setPedidos(dataPedidos);
    } catch (err) {
      console.error(err);
    } finally {
      setCargandoProductos(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUsuarioLogueado(null);
  };

  const cambiarCantidadTemp = (productoId: number, delta: number) => {
    const prod = productos.find(p => p.id === productoId);
    if (!prod) return;
    const actual = cantidadesTemp[productoId] || 0;
    const nueva = actual + delta;
    const stockDisponibles = (prod.stock_disponible !== undefined) ? prod.stock_disponible : (prod.stock_fisico - (prod.stock_reservado || 0));
    if (nueva < 0) return;
    if (nueva > stockDisponibles) { alert("No hay suficiente stock disponible en depósito."); return; }
    setCantidadesTemp({ ...cantidadesTemp, [productoId]: nueva });
  };

  const agregarAlCarritoDesdeCatalogo = (productoId: number) => {
    const cantidadSeleccionada = cantidadesTemp[productoId] || 0;
    if (cantidadSeleccionada <= 0) { alert("Selecciona al menos 1 unidad para agregar."); return; }
    const prod = productos.find(p => p.id === productoId);
    if (!prod) return;
    const stockDisponibles = (prod.stock_disponible !== undefined) ? prod.stock_disponible : (prod.stock_fisico - (prod.stock_reservado || 0));
    if (stockDisponibles < cantidadSeleccionada) { alert("Stock disponible insuficiente."); return; }
    
    setProductos(productos.map(p => {
      if (p.id === productoId) {
        const nuevoReservado = (p.stock_reservado || 0) + cantidadSeleccionada;
        return { ...p, stock_reservado: nuevoReservado, stock_disponible: p.stock_fisico - nuevoReservado };
      }
      return p;
    }));

    const carritoActual = carrito[productoId] || 0;
    setCarrito({ ...carrito, [productoId]: carritoActual + cantidadSeleccionada });
    setCantidadesTemp({ ...cantidadesTemp, [productoId]: 0 });
  };

  const ajustarCantidadCarrito = (productoId: number, nuevaCant: number) => {
    const prodOriginal = productos.find(p => p.id === productoId);
    if (!prodOriginal) return;
    const cantActualEnCarrito = carrito[productoId] || 0;
    const diferencia = nuevaCant - cantActualEnCarrito;
    const stockDisponibles = (prodOriginal.stock_disponible !== undefined) ? prodOriginal.stock_disponible : (prodOriginal.stock_fisico - (prodOriginal.stock_reservado || 0));
    if (diferencia > 0 && stockDisponibles < diferencia) { alert("Stock disponible insuficiente en depósito."); return; }
    
    setProductos(productos.map(p => {
      if (p.id === productoId) {
        const nuevoReservado = (p.stock_reservado || 0) + diferencia;
        return { ...p, stock_reservado: nuevoReservado, stock_disponible: p.stock_fisico - nuevoReservado };
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
        const nuevoReservado = Math.max(0, (p.stock_reservado || 0) - cantEnCarrito);
        return { ...p, stock_reservado: nuevoReservado, stock_disponible: p.stock_fisico - nuevoReservado };
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
    if (!id) { setRazonSocial(''); setCuit(''); setDireccion(''); setTelefono(''); return; }
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
    if (!razonSocial || !cuit || !direccion) { alert("Complete los campos obligatorios."); return; }
    const payload = { razon_social: razonSocial, cuit, direccion, condicion_fiscal: condicionFiscal, medio_pago: medioPago, telefono };
    const token = localStorage.getItem('token');
    const headers = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` };
    try {
      if (modoCliente === 'editar' && clienteEditandoId) {
        await fetch(`${API_URL}/clientes/${clienteEditandoId}`, { method: 'PUT', headers, body: JSON.stringify(payload) });
      } else {
        await fetch(`${API_URL}/clientes`, { method: 'POST', headers, body: JSON.stringify(payload) });
      }
      await cargarDatosIniciales();
      setModoCliente('lista');
      setClienteEditandoId(null);
      setRazonSocial(''); setCuit(''); setDireccion(''); setTelefono('');
    } catch (err) { alert("Error al guardar cliente."); }
  };

  const eliminarClienteDirecto = async (id: number) => {
    if (!confirm("¿Desea eliminar este cliente?")) return;
    const token = localStorage.getItem('token');
    await fetch(`${API_URL}/clientes/${id}`, { method: 'DELETE', headers: { 'Authorization': `Bearer ${token}` } });
    cargarDatosIniciales();
  };

  const enviarPedido = async () => {
    setMensajePedido('');
    const items = Object.entries(carrito).map(([idStr, cantidad]) => ({ producto_id: Number(idStr), cantidad: Number(cantidad) }));
    if (items.length === 0) { alert("El carrito está vacío."); return; }
    if (!razonSocial || !cuit || !direccion) { alert("Complete los datos del cliente."); return; }

    try {
      const bodyData = clienteSeleccionadoId ? {
        cliente_id: Number(clienteSeleccionadoId),
        observaciones_agente: observaciones,
        fecha_entrega: fechaEntrega || undefined,
        items: items
      } : {
        datos_cliente: { razon_social: razonSocial, cuit, direccion, condicion_fiscal: condicionFiscal, medio_pago: medioPago, telefono },
        observaciones_agente: observaciones,
        fecha_entrega: fechaEntrega || undefined,
        items: items
      };

      const token = localStorage.getItem('token');
      const response = await fetch(`${API_URL}/pedidos`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
        body: JSON.stringify(bodyData)
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Error al procesar pedido.");

      setMensajePedido(`¡Orden #${data.pedido_id} generada con éxito y reservada en depósito!`);
      setTimeout(() => { setMensajePedido(''); }, 2500);

      setCarrito({});
      setCantidadesTemp({});
      setObservaciones('');
      setFechaEntrega('');
      setCarritoAbierto(false);
      cargarDatosIniciales();
    } catch (err: any) { alert(`Error: ${err.message}`); }
  };

  const avanzarEstadoPedido = async (pedidoId: number, nuevoEstado: string) => {
    if (!confirm(`¿Estás seguro de avanzar el pedido #${pedidoId} a "${nuevoEstado}"?`)) return;
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/pedidos/${pedidoId}/estado`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ nuevo_estado: nuevoEstado })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Error al cambiar estado");
      alert(data.mensaje);
      cargarDatosIniciales();
    } catch (err: any) { alert(`Error: ${err.message}`); }
  };

  const abrirSeguimiento = async (pedido: any) => {
    setPedidoSeleccionado(pedido);
    setModalSeguimientoAbierto(true);
    setLineaTiempo([]);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_URL}/pedidos/${pedido.id}/seguimiento`, { headers: { 'Authorization': `Bearer ${token}` } });
      setLineaTiempo(await res.json());
    } catch (err) { console.error(err); }
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

  const pedidosAgrupados = pedidos.reduce((acc: Record<string, any[]>, ped: any) => {
    const fecha = ped.fecha_entrega || 'Sin fecha asignada';
    if (!acc[fecha]) acc[fecha] = [];
    acc[fecha].push(ped);
    return acc;
  }, {} as Record<string, any[]>);

  const fechasOrdenadas = Object.keys(pedidosAgrupados).sort((a, b) => {
    if (a === 'Sin fecha asignada') return 1;
    if (b === 'Sin fecha asignada') return -1;
    return a.localeCompare(b);
  });

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', paddingBottom: '60px', fontFamily: 'Inter, sans-serif', width: '100%', boxSizing: 'border-box' }}>
      
      {/* NAVBAR RESPONSIVO Y FLUIDO */}
      <header className="navbar-gradient" style={{ padding: '16px 32px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '12px', position: 'sticky', top: 0, zIndex: 1000, width: '100%', boxSizing: 'border-box' }}>
        
        {/* Logo y Botón Menú Móvil */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button onClick={() => setMenuMovilAbierto(!menuMovilAbierto)} style={{ display: 'none', background: 'rgba(255,255,255,0.1)', border: 'none', color: '#fff', padding: '8px', borderRadius: '10px', cursor: 'pointer' }} className="mobile-menu-btn">
            <Menu size={22} />
          </button>
          
          <div onClick={() => setVistaActual('catalogo')} style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
            <div style={{ background: '#3b82f6', width: '40px', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '12px', boxShadow: '0 4px 10px rgba(59,130,246,0.3)' }}>
              <Truck size={22} color="#fff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ margin: '0', fontSize: '18px', fontWeight: '800', color: '#fff', letterSpacing: '-0.5px' }}>DistriApp</h2>
                <span style={{ background: 'rgba(255,255,255,0.2)', padding: '2px 6px', borderRadius: '6px', fontSize: '10px', fontWeight: 'bold' }}>PWA</span>
              </div>
              <p style={{ margin: '0', fontSize: '10px', opacity: 0.7, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Preventa & Pedidos</p>
            </div>
          </div>
        </div>

        {/* Botones de Navegación Centrales (Escritorio) */}
        <div style={{ display: 'flex', gap: '8px', background: 'rgba(0,0,0,0.2)', padding: '6px', borderRadius: '14px' }} className="desktop-nav">
          <button onClick={() => setVistaActual('catalogo')} style={{ background: vistaActual === 'catalogo' ? '#2563eb' : 'transparent', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '10px', fontSize: '13px', fontWeight: '600', cursor: 'pointer', transition: 'all 0.2s' }}>📦 Catálogo</button>
          <button onClick={() => setVistaActual('clientes')} style={{ background: vistaActual === 'clientes' ? '#2563eb' : 'transparent', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '10px', fontSize: '13px', fontWeight: '600', cursor: 'pointer', transition: 'all 0.2s' }}>👥 Clientes</button>
          <button onClick={() => setVistaActual('historial')} style={{ background: vistaActual === 'historial' ? '#2563eb' : 'transparent', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '10px', fontSize: '13px', fontWeight: '600', cursor: 'pointer', transition: 'all 0.2s' }}>📋 Pedidos</button>
        </div>

        {/* Acciones de Derecha (Carrito y Usuario) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginLeft: 'auto' }}>
          <button onClick={() => setCarritoAbierto(true)} style={{ background: '#10b981', border: 'none', color: '#fff', fontSize: '13px', padding: '10px 16px', borderRadius: '12px', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'bold', cursor: 'pointer', boxShadow: '0 4px 12px rgba(16,185,129,0.3)', whiteSpace: 'nowrap' }}>
            <ShoppingCart size={16} /> Carrito {cantidadTotalItems() > 0 && <span style={{ background: '#fff', color: '#10b981', fontSize: '11px', padding: '2px 8px', borderRadius: '50px', fontWeight: '800' }}>{cantidadTotalItems()}</span>}
          </button>
          
          <UserMenuDropdown usuario={usuarioLogueado} onOpenChangePassword={() => setIsChangePasswordOpen(true)} onLogout={handleLogout} />
        </div>

        {/* Menú Desplegable Móvil */}
        {menuMovilAbierto && (
          <div className="animate-slide-down" style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '8px', paddingTop: '12px', borderTop: '1px solid rgba(255,255,255,0.15)' }}>
            <button onClick={() => { setVistaActual('catalogo'); setMenuMovilAbierto(false); }} style={{ background: vistaActual === 'catalogo' ? '#2563eb' : 'rgba(255,255,255,0.05)', color: '#fff', border: 'none', padding: '12px 16px', borderRadius: '10px', fontSize: '14px', fontWeight: '600', textAlign: 'left', cursor: 'pointer' }}>📦 Catálogo</button>
            <button onClick={() => { setVistaActual('clientes'); setMenuMovilAbierto(false); }} style={{ background: vistaActual === 'clientes' ? '#2563eb' : 'rgba(255,255,255,0.05)', color: '#fff', border: 'none', padding: '12px 16px', borderRadius: '10px', fontSize: '14px', fontWeight: '600', textAlign: 'left', cursor: 'pointer' }}>👥 Clientes</button>
            <button onClick={() => { setVistaActual('historial'); setMenuMovilAbierto(false); }} style={{ background: vistaActual === 'historial' ? '#2563eb' : 'rgba(255,255,255,0.05)', color: '#fff', border: 'none', padding: '12px 16px', borderRadius: '10px', fontSize: '14px', fontWeight: '600', textAlign: 'left', cursor: 'pointer' }}>📋 Pedidos</button>
          </div>
        )}
      </header>

      <style>{`@media (max-width: 900px) { .desktop-nav { display: none !important; } .mobile-menu-btn { display: flex !important; } }`}</style>

      <ChangePasswordModal isOpen={isChangePasswordOpen} onClose={() => setIsChangePasswordOpen(false)} usuarioId={usuarioLogueado?.id || 1} />

      <main style={{ maxWidth: '1400px', margin: '0 auto', padding: '32px 24px', width: '100%' }}>
        {mensajePedido && <div className="animate-fade-in" style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '16px 20px', borderRadius: '14px', marginBottom: '30px', color: '#166534', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '10px', boxShadow: '0 2px 5px rgba(0,0,0,0.02)' }}><CheckCircle2 size={20} color="#16a34a" />{mensajePedido}</div>}

        {/* VISTA 1: CATÁLOGO */}
        {vistaActual === 'catalogo' && (
          <div>
            <div style={{ background: '#fff', padding: '24px 30px', borderRadius: '20px', border: '1px solid #e2e8f0', marginBottom: '25px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '15px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
              <div>
                <h2 style={{ color: '#0f172a', margin: '0 0 6px 0', fontSize: '24px', fontWeight: '800', letterSpacing: '-0.5px' }}>Catálogo de Productos</h2>
                <p style={{ margin: '0', fontSize: '14px', color: '#64748b' }}>Selecciona los productos y presiona "Agregar" para incorporarlos al pedido.</p>
              </div>
              <input type="text" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} placeholder="Buscar por nombre o SKU..." style={{ width: '320px', maxWidth: '100%', padding: '12px 16px', borderRadius: '12px', border: '1px solid #cbd5e1', fontSize: '14px', outline: 'none', background: '#f8fafc' }} />
            </div>

            <div style={{ display: 'flex', gap: '10px', marginBottom: '25px', overflowX: 'auto', paddingBottom: '5px' }}>
              {['Todas', 'Ropa y Lavado', 'Superficies y Pisos', 'Baños y Sanitarios', 'Cocina y Desengrasantes', 'Accesorios y Utensilios'].map(cat => (
                <button key={cat} onClick={() => setCategoriaSeleccionada(cat)} style={{ padding: '10px 18px', borderRadius: '24px', border: '1px solid #cbd5e1', background: categoriaSeleccionada === cat ? '#1e3a8a' : '#fff', color: categoriaSeleccionada === cat ? '#fff' : '#475569', fontSize: '13px', fontWeight: '600', cursor: 'pointer', whiteSpace: 'nowrap', boxShadow: '0 2px 4px rgba(0,0,0,0.02)', transition: 'all 0.2s' }}>{cat}</button>
              ))}
            </div>

            {cargandoProductos ? <p style={{ textAlign: 'center', padding: '60px', color: '#64748b', fontSize: '15px' }}>Cargando productos del sistema...</p> : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
                {productosFiltrados.map(prod => {
                  const cantTemp = cantidadesTemp[prod.id] || 0;
                  const stockDisponibleReal = (prod.stock_disponible !== undefined) ? prod.stock_disponible : (prod.stock_fisico - (prod.stock_reservado || 0));
                  return (
                    <div key={prod.id} className="card-producto">
                      <div style={{ width: '100%', height: '180px', backgroundColor: '#f8fafc', borderRadius: '16px', marginBottom: '16px', overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid #e2e8f0' }}>
                        <img src={prod.imagen_url && prod.imagen_url !== 'default.png' ? prod.imagen_url : 'https://cdn-icons-png.flaticon.com/512/679/679720.png'} alt={prod.nombre} style={{ width: '100%', height: '100%', objectFit: 'contain', padding: '16px' }} />
                      </div>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                          <span style={{ background: '#eff6ff', color: '#1e3a8a', border: '1px solid #dbeafe', padding: '4px 10px', borderRadius: '8px', fontSize: '12px', fontWeight: 'bold' }}>{prod.codigo}</span>
                          <span style={{ background: stockDisponibleReal > 0 ? '#f0fdf4' : '#fef2f2', color: stockDisponibleReal > 0 ? '#16a34a' : '#dc2626', border: `1px solid ${stockDisponibleReal > 0 ? '#bbf7d0' : '#fecaca'}`, padding: '4px 10px', borderRadius: '8px', fontSize: '12px', fontWeight: 'bold' }}>Disponible: {stockDisponibleReal}</span>
                        </div>
                        <h4 style={{ margin: '8px 0 10px 0', fontSize: '16px', color: '#0f172a', fontWeight: '700', lineHeight: '1.4' }}>{prod.nombre}</h4>
                        <p style={{ fontSize: '22px', fontWeight: '800', color: '#1e3a8a', margin: '0 0 10px 0' }}>${prod.precio.toLocaleString('es-AR')}</p>
                      </div>
                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '16px', marginTop: '10px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', border: '1px solid #cbd5e1', borderRadius: '12px', background: '#f8fafc', overflow: 'hidden', width: '120px' }}>
                          <button onClick={() => cambiarCantidadTemp(prod.id, -1)} style={{ background: 'none', border: 'none', padding: '10px 12px', cursor: 'pointer', fontWeight: 'bold', color: '#475569' }}>-</button>
                          <input type="number" min="1" max={stockDisponibleReal} value={cantTemp === 0 ? '' : cantTemp} onChange={(e) => {
                            const val = parseInt(e.target.value);
                            const nuevaCant = isNaN(val) ? 0 : val;
                            if (nuevaCant > stockDisponibleReal) {
                              alert(`Solo hay ${stockDisponibleReal} unidades disponibles de este producto.`);
                              setCantidadesTemp({ ...cantidadesTemp, [prod.id]: stockDisponibleReal });
                            } else {
                              setCantidadesTemp({ ...cantidadesTemp, [prod.id]: nuevaCant });
                            }
                          }} style={{ width: '40px', textAlign: 'center', border: 'none', background: 'transparent', fontSize: '14px', fontWeight: 'bold', color: '#0f172a', outline: 'none', padding: 0 }} placeholder="0" />
                          <button onClick={() => cambiarCantidadTemp(prod.id, 1)} style={{ background: 'none', border: 'none', padding: '10px 12px', cursor: 'pointer', fontWeight: 'bold', color: '#475569' }}>+</button>
                        </div>
                        <button onClick={() => agregarAlCarritoDesdeCatalogo(prod.id)} className="btn-primary" style={{ flex: 1, padding: '12px' }}>Agregar</button>
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
            <div style={{ background: '#fff', padding: '24px 30px', borderRadius: '20px', border: '1px solid #e2e8f0', marginBottom: '25px', display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '15px' }}>
              <div>
                <h2 style={{ color: '#0f172a', margin: '0 0 4px 0', fontSize: '24px', fontWeight: '800' }}>Mis Clientes B2B</h2>
                <p style={{ margin: '0', fontSize: '14px', color: '#64748b' }}>Administración de cuentas comerciales y datos fiscales.</p>
              </div>
              {modoCliente === 'lista' && (
                <button onClick={() => { setModoCliente('crear'); setClienteEditandoId(null); setRazonSocial(''); setCuit(''); setDireccion(''); setTelefono(''); }} className="btn-primary" style={{ background: '#16a34a', boxShadow: '0 4px 10px rgba(22,163,74,0.2)' }}>+ Nuevo Cliente</button>
              )}
            </div>

            {modoCliente !== 'lista' ? (
              <div style={{ background: '#fff', padding: '30px', borderRadius: '20px', border: '1px solid #e2e8f0', maxWidth: '650px', margin: '0 auto', boxShadow: '0 10px 25px rgba(0,0,0,0.05)' }}>
                <h3 style={{ marginTop: 0, color: '#0f172a', fontSize: '20px', fontWeight: '700', marginBottom: '20px' }}>{modoCliente === 'crear' ? 'Registrar Nuevo Cliente' : 'Modificar Cliente'}</h3>
                <form onSubmit={guardarClienteManual} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Razón Social *</label>
                    <input type="text" value={razonSocial} onChange={(e) => setRazonSocial(e.target.value)} required />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>CUIT / DNI *</label>
                      <input type="text" value={cuit} onChange={(e) => setCuit(e.target.value)} required />
                    </div>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Teléfono / WhatsApp</label>
                      <input type="text" value={telefono} onChange={(e) => setTelefono(e.target.value)} />
                    </div>
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Dirección de Entrega *</label>
                    <input type="text" value={direccion} onChange={(e) => setDireccion(e.target.value)} required />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Condición Fiscal</label>
                      <select value={condicionFiscal} onChange={(e) => setCondicionFiscal(e.target.value)}>
                        <option>Responsable Inscripto</option>
                        <option>Monotributo</option>
                        <option>Consumidor Final</option>
                      </select>
                    </div>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Medio de Pago</label>
                      <select value={medioPago} onChange={(e) => setMedioPago(e.target.value)}>
                        <option>Efectivo contra entrega</option>
                        <option>Transferencia Bancaria</option>
                        <option>Cuenta Corriente 30 días</option>
                      </select>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '12px', marginTop: '10px' }}>
                    <button type="submit" className="btn-primary" style={{ flex: 1 }}>Guardar Cliente</button>
                    <button type="button" onClick={() => setModoCliente('lista')} className="btn-secondary">Cancelar</button>
                  </div>
                </form>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
                {clientes.map(cli => (
                  <div key={cli.id} className="card-producto" style={{ padding: '22px' }}>
                    <div>
                      <h4 style={{ margin: '0 0 10px 0', color: '#1e3a8a', fontSize: '18px', fontWeight: '700' }}>{cli.razon_social}</h4>
                      <p style={{ margin: '5px 0', fontSize: '14px', color: '#475569' }}><strong>CUIT:</strong> {cli.cuit}</p>
                      <p style={{ margin: '5px 0', fontSize: '14px', color: '#475569' }}><strong>Dir:</strong> {cli.direccion || 'Sin dirección'}</p>
                      <p style={{ margin: '5px 0', fontSize: '14px', color: '#475569' }}><strong>Pago:</strong> {cli.medio_pago || 'Efectivo'}</p>
                    </div>
                    <div style={{ display: 'flex', gap: '10px', marginTop: '20px', borderTop: '1px solid #f1f5f9', paddingTop: '16px' }}>
                      <button onClick={() => { setModoCliente('editar'); setClienteEditandoId(cli.id); setRazonSocial(cli.razon_social); setCuit(cli.cuit); setDireccion(cli.direccion); setCondicionFiscal(cli.condicion_fiscal); setMedioPago(cli.medio_pago); setTelefono(cli.telefono); }} className="btn-secondary" style={{ flex: 1, padding: '10px', color: '#1e3a8a' }}>✏️ Modificar</button>
                      <button onClick={() => eliminarClienteDirecto(cli.id)} style={{ background: '#fef2f2', color: '#dc2626', border: '1px solid #fee2e2', padding: '10px 14px', borderRadius: '10px', fontWeight: 'bold', cursor: 'pointer', fontSize: '14px' }}>🗑️</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* VISTA 3: HISTORIAL DE PEDIDOS AGRUPADO POR FECHA */}
        {vistaActual === 'historial' && (
          <div>
            <div style={{ background: '#fff', padding: '24px 30px', borderRadius: '20px', border: '1px solid #e2e8f0', marginBottom: '25px' }}>
              <h2 style={{ color: '#0f172a', margin: '0 0 4px 0', fontSize: '24px', fontWeight: '800' }}>Historial de Órdenes & PDFs</h2>
              <p style={{ margin: '0', fontSize: '14px', color: '#64748b' }}>Pedidos agrupados por fecha de entrega programada.</p>
            </div>

            {pedidos.length === 0 ? <p style={{ textAlign: 'center', padding: '60px', color: '#64748b', fontSize: '16px' }}>No hay pedidos registrados.</p> : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
                {fechasOrdenadas.map(fecha => (
                  <div key={fecha}>
                    {/* Encabezado del grupo de fecha */}
                    <h3 style={{ fontSize: '18px', fontWeight: 'bold', color: '#1e3a8a', marginBottom: '16px', paddingBottom: '8px', borderBottom: '2px solid #e2e8f0' }}>
                      📅 Entrega: {fecha === 'Sin fecha asignada' ? 'Sin fecha asignada' : new Date(fecha + 'T00:00:00').toLocaleDateString('es-AR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
                    </h3>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      {pedidosAgrupados[fecha].map(ped => (
                        <div key={ped.id} className="card-producto" style={{ padding: '20px 26px', flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '15px' }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
                              <h4 style={{ margin: '0', color: '#1e3a8a', fontSize: '18px', fontWeight: '700' }}>Orden #{ped.id} - {ped.razon_social || 'Cliente General'}</h4>
                              <span style={{ background: '#eff6ff', color: '#1d4ed8', border: '1px solid #dbeafe', padding: '4px 10px', borderRadius: '6px', fontSize: '12px', fontWeight: 'bold' }}>
                                {ped.estado_cliente || ped.estado}
                              </span>
                            </div>
                            <p style={{ margin: '3px 0', fontSize: '14px', color: '#64748b' }}>📅 Fecha de creación: {ped.fecha}</p>
                            <p style={{ margin: '3px 0', fontSize: '14px', color: '#475569' }}>📝 Obs: {ped.observaciones_agente || 'Ninguna'}</p>
                          </div>
                          <div style={{ textAlign: 'right', display: 'flex', alignItems: 'center', gap: '15px' }}>
                            
                            <button onClick={() => abrirSeguimiento(ped)} className="btn-secondary" style={{ padding: '10px 16px', fontSize: '13px' }}>🕒 Seguimiento</button>

                            {usuarioLogueado?.rol === 'admin' && ped.estado === 'RECIBIDO' && (
                              <button onClick={() => avanzarEstadoPedido(ped.id, 'VALIDADO')} className="btn-primary" style={{ background: '#16a34a', boxShadow: '0 4px 10px rgba(22,163,74,0.2)', padding: '10px 16px', fontSize: '13px' }}>⚡ Avanzar (Validar)</button>
                            )}
                            {usuarioLogueado?.rol === 'admin' && ped.estado === 'VALIDADO' && (
                              <button onClick={() => avanzarEstadoPedido(ped.id, 'PREPARADO')} className="btn-primary" style={{ padding: '10px 16px', fontSize: '13px' }}>📦 Avanzar (Preparar)</button>
                            )}

                            <div>
                              <span style={{ fontSize: '12px', color: '#64748b', display: 'block' }}>Total</span>
                              <span style={{ fontSize: '20px', fontWeight: '800', color: '#1e3a8a' }}>${ped.total.toLocaleString('es-AR')}</span>
                            </div>
                            <a href={`http://localhost:8001/documentos_pedidos/orden_pedido_${ped.id}.pdf`} target="_blank" rel="noopener noreferrer" style={{ background: '#dc2626', color: '#fff', padding: '10px 20px', borderRadius: '12px', fontSize: '13px', fontWeight: 'bold', textDecoration: 'none', boxShadow: '0 4px 10px rgba(220,38,38,0.2)' }}>📄 PDF</a>
                          </div>
                        </div>
                      ))}
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
          <div onClick={() => setCarritoAbierto(false)} className="animate-fade-in" style={{ position: 'absolute', inset: 0, background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(4px)' }} />

          <div className="animate-slide-in-right" style={{ position: 'relative', marginLeft: 'auto', width: '480px', maxWidth: '100%', height: '100vh', maxHeight: '100vh', background: '#f8fafc', boxShadow: '-15px 0 40px rgba(0,0,0,0.2)', display: 'flex', flexDirection: 'column', boxSizing: 'border-box', zIndex: 2010, overflow: 'hidden' }}>
            
            {/* Cabecera del Carrito - Blanca y limpia */}
            <div style={{ background: '#ffffff', color: '#0f172a', padding: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #e2e8f0', flexShrink: 0 }}>
              <div>
                <h3 style={{ margin: '0', fontSize: '20px', fontWeight: '800', color: '#0f172a' }}>Carrito de Compras</h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#64748b' }}>Revisá y confirma tu pedido</p>
              </div>
              <button onClick={() => setCarritoAbierto(false)} style={{ background: '#f1f5f9', border: 'none', color: '#334155', padding: '8px', borderRadius: '10px', cursor: 'pointer' }}><X size={20} /></button>
            </div>

            {/* Zona Central - Fondo gris suave y textos oscuros */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '24px', minHeight: 0 }}>
              
              {/* Lista de Artículos */}
              <div>
                <h4 style={{ margin: '0 0 12px 0', fontSize: '12px', color: '#64748b', textTransform: 'uppercase', fontWeight: '700', letterSpacing: '0.5px' }}>Artículos Seleccionados ({cantidadTotalItems()})</h4>
                {Object.keys(carrito).length === 0 ? <p style={{ color: '#64748b', fontSize: '14px', fontStyle: 'italic' }}>El carrito está vacío.</p> : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    {Object.entries(carrito).map(([idStr, cant]) => {
                      const prod = productos.find(p => p.id === Number(idStr));
                      if (!prod) return null;
                      return (
                        <div key={idStr} style={{ background: '#ffffff', padding: '16px', borderRadius: '16px', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                          <div>
                            <strong style={{ fontSize: '14px', display: 'block', color: '#0f172a', fontWeight: '700' }}>{prod.nombre}</strong>
                            <span style={{ fontSize: '13px', color: '#64748b', marginTop: '4px', display: 'block' }}>${prod.precio.toLocaleString('es-AR')} c/u</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <input type="number" min="1" value={cant} onChange={(e) => ajustarCantidadCarrito(prod.id, parseInt(e.target.value) || 0)} style={{ width: '56px', textAlign: 'center', padding: '8px', borderRadius: '10px', border: '1px solid #cbd5e1', fontSize: '14px', color: '#0f172a', background: '#f8fafc' }} />
                            <button onClick={() => eliminarDelCarrito(prod.id)} style={{ background: '#fef2f2', border: 'none', color: '#dc2626', cursor: 'pointer', padding: '8px', borderRadius: '8px' }} title="Eliminar"><X size={16} /></button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* Totalizador */}
              <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', padding: '20px', borderRadius: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '16px', fontWeight: '700', color: '#1e3a8a' }}>Total Pedido:</span>
                <span style={{ fontSize: '24px', fontWeight: '800', color: '#1e3a8a' }}>${calcularTotal().toLocaleString('es-AR')}</span>
              </div>

              {/* Formulario de Cliente */}
              <div style={{ background: '#ffffff', border: '1px solid #e2e8f0', borderRadius: '16px', padding: '24px', boxShadow: '0 2px 4px rgba(0,0,0,0.02)' }}>
                <h4 style={{ margin: '0 0 16px 0', fontSize: '13px', color: '#1e3a8a', textTransform: 'uppercase', fontWeight: '800', letterSpacing: '0.5px' }}>Datos del Cliente</h4>
                
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ fontSize: '12px', fontWeight: '700', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Seleccionar de "Mis Clientes"</label>
                  <select value={clienteSeleccionadoId} onChange={seleccionarClienteExistente} style={{ width: '100%', padding: '12px', borderRadius: '10px', border: '1px solid #cbd5e1', background: '#f8fafc', color: '#0f172a', fontSize: '14px' }}>
                    <option value="">-- Cargar manualmente o nuevo cliente --</option>
                    {clientes.map(c => <option key={c.id} value={c.id}>{c.razon_social} (CUIT: {c.cuit})</option>)}
                  </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: '700', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Razón Social / Nombre *</label>
                    <input type="text" value={razonSocial} onChange={(e) => setRazonSocial(e.target.value)} placeholder="Ej. Kiosco Belgrano" style={{ background: '#f8fafc', color: '#0f172a' }} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: '700', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>CUIT / DNI *</label>
                      <input type="text" value={cuit} onChange={(e) => setCuit(e.target.value)} placeholder="Ej. 30-7123" style={{ background: '#f8fafc', color: '#0f172a' }} />
                    </div>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: '700', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Teléfono</label>
                      <input type="text" value={telefono} onChange={(e) => setTelefono(e.target.value)} placeholder="Ej. 115566" style={{ background: '#f8fafc', color: '#0f172a' }} />
                    </div>
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: '700', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Dirección de Entrega *</label>
                    <input type="text" value={direccion} onChange={(e) => setDireccion(e.target.value)} placeholder="Ej. Av. San Martín 1420" style={{ background: '#f8fafc', color: '#0f172a' }} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: '700', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Condición Fiscal</label>
                      <select value={condicionFiscal} onChange={(e) => setCondicionFiscal(e.target.value)} style={{ background: '#f8fafc', color: '#0f172a' }}>
                        <option>Responsable Inscripto</option>
                        <option>Monotributo</option>
                        <option>Consumidor Final</option>
                      </select>
                    </div>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: '700', color: '#475569', display: 'block', marginBottom: '6px', textTransform: 'uppercase' }}>Medio de Pago</label>
                      <select value={medioPago} onChange={(e) => setMedioPago(e.target.value)} style={{ background: '#f8fafc', color: '#0f172a' }}>
                        <option>Efectivo contra entrega</option>
                        <option>Transferencia Bancaria</option>
                        <option>Cuenta Corriente 30 días</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#475569', marginBottom: '6px', textTransform: 'uppercase' }}>Fecha de Entrega (opcional)</label>
                <input type="date" value={fechaEntrega} onChange={(e) => setFechaEntrega(e.target.value)} style={{ background: '#f8fafc', color: '#0f172a' }} />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '700', color: '#475569', marginBottom: '6px', textTransform: 'uppercase' }}>Observaciones del Pedido</label>
                <textarea value={observaciones} onChange={(e) => setObservaciones(e.target.value)} placeholder="Horarios de descarga..." rows={3} style={{ background: '#f8fafc', color: '#0f172a' }} />
              </div>
            </div>

            {/* Botón de Confirmar */}
            <div style={{ padding: '24px', background: '#ffffff', borderTop: '1px solid #e2e8f0', flexShrink: 0 }}>
              <button onClick={enviarPedido} className="btn-primary" style={{ width: '100%', padding: '16px', fontSize: '16px', fontWeight: '800', borderRadius: '14px' }}>Confirmar y Generar PDF</button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL DE LÍNEA DE TIEMPO */}
      {modalSeguimientoAbierto && pedidoSeleccionado && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000, padding: '20px' }}>
          <div className="animate-fade-in" style={{ background: '#fff', borderRadius: '24px', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.25)', maxWidth: '500px', width: '100%', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
            <div style={{ background: '#1e3a8a', padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: '#fff' }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 'bold' }}>Seguimiento del Pedido #{pedidoSeleccionado.id}</h3>
                <p style={{ margin: '4px 0 0 0', fontSize: '13px', opacity: 0.8 }}>{pedidoSeleccionado.razon_social}</p>
              </div>
              <button onClick={() => setModalSeguimientoAbierto(false)} style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', opacity: 0.8 }}><X size={20} /></button>
            </div>
            
            <div style={{ padding: '30px', maxHeight: '60vh', overflowY: 'auto' }}>
              {lineaTiempo.length === 0 ? (
                <p style={{ textAlign: 'center', color: '#64748b' }}>Cargando historial...</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  {lineaTiempo.map((evento, index) => (
                    <div key={index} style={{ display: 'flex', gap: '15px' }}>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: index === lineaTiempo.length - 1 ? '#2563eb' : '#cbd5e1', border: '2px solid #fff', boxShadow: '0 0 0 2px ' + (index === lineaTiempo.length - 1 ? '#bfdbfe' : '#f1f5f9') }}></div>
                        {index < lineaTiempo.length - 1 && <div style={{ width: '2px', flex: 1, background: '#e2e8f0', margin: '4px 0' }}></div>}
                      </div>
                      <div style={{ paddingBottom: '15px' }}>
                        <p style={{ margin: '0 0 4px 0', fontWeight: 'bold', fontSize: '15px', color: index === lineaTiempo.length - 1 ? '#1e3a8a' : '#334155' }}>
                          {evento.estado_cliente}
                        </p>
                        <p style={{ margin: 0, fontSize: '13px', color: '#64748b' }}>
                          📅 {evento.fecha} <br/> 👤 Por: {evento.cambiado_por}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div style={{ padding: '20px 24px', background: '#f8fafc', borderTop: '1px solid #e2e8f0', textAlign: 'right' }}>
              <button onClick={() => setModalSeguimientoAbierto(false)} className="btn-secondary">Cerrar</button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}