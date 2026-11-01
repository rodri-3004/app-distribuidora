// frontend/src/App.tsx
import { useState, useEffect } from 'react';
import { obtenerProductos } from './services/api';
import { AuthView } from './components/AuthView';
import './App.css';

export default function App() {
  const [usuarioLogueado, setUsuarioLogueado] = useState<any>(null);
  
  const [productos, setProductos] = useState<any[]>([]);
  const [clientes, setClientes] = useState<any[]>([]);
  const [pedidos, setPedidos] = useState<any[]>([]);
  
  const [categoriaSeleccionada, setCategoriaSeleccionada] = useState<string>('Todas');
  const [busqueda, setBusqueda] = useState<string>('');
  const [cargandoProductos, setCargandoProductos] = useState(false);

  // Cantidades temporales en las tarjetas del catálogo antes de dar "Agregar"
  const [cantidadesTemp, setCantidadesTemp] = useState<{ [key: number]: number }>({});

  // Carrito definitivo y Navegación
  const [carrito, setCarrito] = useState<{ [key: number]: number }>({});
  const [observaciones, setObservaciones] = useState('');
  const [mensajePedido, setMensajePedido] = useState('');
  const [vistaActual, setVistaActual] = useState<'catalogo' | 'clientes' | 'historial'>('catalogo');
  const [carritoAbierto, setCarritoAbierto] = useState(false);

  // Datos del cliente en el carrito
  const [clienteSeleccionadoId, setClienteSeleccionadoId] = useState<string>('');
  const [razonSocial, setRazonSocial] = useState('');
  const [cuit, setCuit] = useState('');
  const [direccion, setDireccion] = useState('');
  const [condicionFiscal, setCondicionFiscal] = useState('Responsable Inscripto');
  const [medioPago, setMedioPago] = useState('Efectivo contra entrega');
  const [telefono, setTelefono] = useState('');

  // Estados para módulo Mis Clientes (CRUD)
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

      const resClientes = await fetch("http://127.0.0.1:8001/clientes");
      const dataClientes = await resClientes.json();
      setClientes(dataClientes);

      const resPedidos = await fetch("http://127.0.0.1:8001/pedidos/todos");
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
        await fetch(`http://127.0.0.1:8001/clientes/${clienteEditandoId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
      } else {
        await fetch(`http://127.0.0.1:8001/clientes`, {
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
    await fetch(`http://127.0.0.1:8001/clientes/${id}`, { method: 'DELETE' });
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

      const response = await fetch("http://127.0.0.1:8001/pedidos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(bodyData)
      });

      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Error al procesar pedido.");

      setMensajePedido(`¡Orden #${data.pedido_id} generada con éxito!`);
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
    <div style={{ minHeight: '100vh', background: '#f1f5f9', paddingBottom: '40px', fontFamily: 'system-ui, sans-serif' }}>
      
      {/* NAVBAR */}
      <header style={{ background: '#1e3a8a', color: '#ffffff', padding: '12px 35px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 4px 20px rgba(30, 58, 138, 0.2)' }}>
        <div onClick={() => setVistaActual('catalogo')} style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}>
          <div style={{ background: '#3b82f6', width: '38px', height: '38px', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '18px' }}>📦</div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ margin: '0', fontSize: '18px', fontWeight: '700', color: '#fff' }}>DistriApp</h2>
              <span style={{ background: '#2563eb', padding: '1px 6px', borderRadius: '4px', fontSize: '10px', fontWeight: 'bold' }}>PWA</span>
            </div>
            <p style={{ margin: '0', fontSize: '10px', opacity: 0.8, textTransform: 'uppercase' }}>Sistema de Preventa & Pedidos</p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '8px', background: 'rgba(255,255,255,0.08)', padding: '4px', borderRadius: '12px' }}>
          <button onClick={() => setVistaActual('catalogo')} style={{ background: vistaActual === 'catalogo' ? '#2563eb' : 'transparent', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}>📦 Catálogo & Pedidos</button>
          <button onClick={() => setVistaActual('clientes')} style={{ background: vistaActual === 'clientes' ? '#2563eb' : 'transparent', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}>👥 Mis Clientes</button>
          <button onClick={() => setVistaActual('historial')} style={{ background: vistaActual === 'historial' ? '#2563eb' : 'transparent', color: '#fff', border: 'none', padding: '8px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}>📋 Historial de Pedidos</button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <button onClick={() => setCarritoAbierto(true)} style={{ background: '#2563eb', border: 'none', color: '#fff', fontSize: '13px', padding: '9px 18px', borderRadius: '10px', display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 'bold', cursor: 'pointer' }}>
            🛒 Carrito {cantidadTotalItems() > 0 && <span style={{ background: '#16a34a', color: '#fff', fontSize: '11px', padding: '1px 6px', borderRadius: '50px' }}>{cantidadTotalItems()}</span>}
          </button>
          
          {/* USUARIO LOGUEADO Y SALIR */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', background: 'rgba(255,255,255,0.1)', padding: '6px 12px', borderRadius: '10px' }}>
            <span style={{ fontSize: '13px', fontWeight: 'bold', color: '#fff' }}>👤 {usuarioLogueado.nombre || 'Rodrigo'}</span>
            <button onClick={() => setUsuarioLogueado(null)} style={{ background: 'none', border: 'none', color: '#fca5a5', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold' }} title="Cerrar Sesión">🚪 Salir</button>
          </div>
        </div>
      </header>

      <main style={{ maxWidth: '1350px', margin: '25px auto', padding: '0 25px' }}>
        {mensajePedido && <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', padding: '16px', borderRadius: '12px', marginBottom: '25px', color: '#166534', fontWeight: '600' }}>{mensajePedido}</div>}

        {/* VISTA 1: CATÁLOGO */}
        {vistaActual === 'catalogo' && (
          <div>
            <div style={{ background: '#fff', padding: '25px 30px', borderRadius: '16px', border: '1px solid #e2e8f0', marginBottom: '25px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ color: '#0f172a', margin: '0 0 4px 0', fontSize: '24px', fontWeight: '800' }}>Catálogo de Productos</h2>
                <p style={{ margin: '0', fontSize: '13px', color: '#64748b' }}>Selecciona los bultos y presiona "Agregar" para incorporarlos al pedido.</p>
              </div>
              <input type="text" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} placeholder="Buscar por nombre o SKU..." style={{ width: '300px', padding: '10px 14px', borderRadius: '12px', border: '1px solid #cbd5e1', fontSize: '13px' }} />
            </div>

            <div style={{ display: 'flex', gap: '10px', marginBottom: '25px', overflowX: 'auto' }}>
              {['Todas', 'Bebidas y Jugos', 'Almacén y Comestibles', 'Snacks y Golosinas', 'Limpieza y Perfumería', 'Lácteos y Fríos'].map(cat => (
                <button key={cat} onClick={() => setCategoriaSeleccionada(cat)} style={{ padding: '8px 18px', borderRadius: '20px', border: '1px solid #cbd5e1', background: categoriaSeleccionada === cat ? '#1e3a8a' : '#fff', color: categoriaSeleccionada === cat ? '#fff' : '#475569', fontSize: '13px', fontWeight: '600', cursor: 'pointer' }}>{cat}</button>
              ))}
            </div>

            {cargandoProductos ? <p style={{ textAlign: 'center', padding: '40px' }}>Cargando...</p> : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
                {productosFiltrados.map(prod => {
                  const cantTemp = cantidadesTemp[prod.id] || 0;
                  return (
                    <div key={prod.id} style={{ background: '#fff', borderRadius: '16px', overflow: 'hidden', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', padding: '18px' }}>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
                          <span style={{ background: '#1e3a8a', color: '#fff', padding: '3px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 'bold' }}>{prod.codigo}</span>
                          <span style={{ background: prod.stock_fisico > 0 ? '#16a34a' : '#dc2626', color: '#fff', padding: '3px 8px', borderRadius: '6px', fontSize: '10px', fontWeight: 'bold' }}>Stock: {prod.stock_fisico}</span>
                        </div>
                        <h4 style={{ margin: '10px 0', fontSize: '16px', color: '#0f172a' }}>{prod.nombre}</h4>
                        <p style={{ fontSize: '18px', fontWeight: '800', color: '#1e3a8a', margin: '15px 0' }}>${prod.precio.toLocaleString('es-AR')}</p>
                      </div>

                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center', borderTop: '1px solid #f1f5f9', paddingTop: '15px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', border: '1px solid #cbd5e1', borderRadius: '8px', background: '#f8fafc' }}>
                          <button onClick={() => cambiarCantidadTemp(prod.id, -1)} style={{ background: 'none', border: 'none', padding: '8px 10px', cursor: 'pointer', fontWeight: 'bold' }}>-</button>
                          <span style={{ padding: '0 6px', fontSize: '13px', fontWeight: 'bold' }}>{cantTemp}</span>
                          <button onClick={() => cambiarCantidadTemp(prod.id, 1)} style={{ background: 'none', border: 'none', padding: '8px 10px', cursor: 'pointer', fontWeight: 'bold' }}>+</button>
                        </div>
                        <button onClick={() => agregarAlCarritoDesdeCatalogo(prod.id)} style={{ flex: 1, background: '#2563eb', color: '#fff', border: 'none', borderRadius: '8px', padding: '10px', fontSize: '13px', fontWeight: 'bold', cursor: 'pointer' }}>🛒 Agregar</button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* VISTA 2: MIS CLIENTES (CRUD) */}
        {vistaActual === 'clientes' && (
          <div>
            <div style={{ background: '#fff', padding: '25px 30px', borderRadius: '16px', border: '1px solid #e2e8f0', marginBottom: '25px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2 style={{ color: '#0f172a', margin: '0 0 4px 0', fontSize: '24px', fontWeight: '800' }}>Mis Clientes B2B</h2>
                <p style={{ margin: '0', fontSize: '13px', color: '#64748b' }}>Administración de cuentas comerciales y datos fiscales.</p>
              </div>
              {modoCliente === 'lista' && (
                <button onClick={() => { setModoCliente('crear'); setClienteEditandoId(null); setRazonSocial(''); setCuit(''); setDireccion(''); setTelefono(''); }} style={{ background: '#16a34a', color: '#fff', border: 'none', padding: '10px 20px', borderRadius: '10px', fontWeight: 'bold', cursor: 'pointer' }}>+ Nuevo Cliente</button>
              )}
            </div>

            {modoCliente !== 'lista' ? (
              <div style={{ background: '#fff', padding: '30px', borderRadius: '16px', border: '1px solid #e2e8f0', maxWidth: '600px', margin: '0 auto' }}>
                <h3 style={{ marginTop: 0 }}>{modoCliente === 'crear' ? 'Registrar Nuevo Cliente' : 'Modificar Cliente'}</h3>
                <form onSubmit={guardarClienteManual} style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569' }}>Razón Social *</label>
                    <input type="text" value={razonSocial} onChange={(e) => setRazonSocial(e.target.value)} required style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569' }}>CUIT / DNI *</label>
                      <input type="text" value={cuit} onChange={(e) => setCuit(e.target.value)} required style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }} />
                    </div>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569' }}>Teléfono / WhatsApp</label>
                      <input type="text" value={telefono} onChange={(e) => setTelefono(e.target.value)} style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }} />
                    </div>
                  </div>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569' }}>Dirección de Entrega *</label>
                    <input type="text" value={direccion} onChange={(e) => setDireccion(e.target.value)} required style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }} />
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569' }}>Condición Fiscal</label>
                      <select value={condicionFiscal} onChange={(e) => setCondicionFiscal(e.target.value)} style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }}>
                        <option>Responsable Inscripto</option>
                        <option>Monotributo</option>
                        <option>Consumidor Final</option>
                      </select>
                    </div>
                    <div>
                      <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#475569' }}>Medio de Pago</label>
                      <select value={medioPago} onChange={(e) => setMedioPago(e.target.value)} style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }}>
                        <option>Efectivo contra entrega</option>
                        <option>Transferencia Bancaria</option>
                        <option>Cuenta Corriente 30 días</option>
                      </select>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
                    <button type="submit" style={{ flex: 1, padding: '12px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>Guardar Cliente</button>
                    <button type="button" onClick={() => setModoCliente('lista')} style={{ padding: '12px', background: '#e2e8f0', color: '#334155', border: 'none', borderRadius: '8px', fontWeight: 'bold', cursor: 'pointer' }}>Cancelar</button>
                  </div>
                </form>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
                {clientes.map(cli => (
                  <div key={cli.id} style={{ background: '#fff', borderRadius: '16px', padding: '20px', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                    <div>
                      <h4 style={{ margin: '0 0 8px 0', color: '#1e3a8a', fontSize: '18px' }}>{cli.razon_social}</h4>
                      <p style={{ margin: '4px 0', fontSize: '13px', color: '#475569' }}><strong>CUIT:</strong> {cli.cuit}</p>
                      <p style={{ margin: '4px 0', fontSize: '13px', color: '#475569' }}><strong>Dir:</strong> {cli.direccion || 'Sin dirección'}</p>
                      <p style={{ margin: '4px 0', fontSize: '13px', color: '#475569' }}><strong>Pago:</strong> {cli.medio_pago || 'Efectivo'}</p>
                    </div>
                    <div style={{ display: 'flex', gap: '10px', marginTop: '20px', borderTop: '1px solid #f1f5f9', paddingTop: '15px' }}>
                      <button onClick={() => { setModoCliente('editar'); setClienteEditandoId(cli.id); setRazonSocial(cli.razon_social); setCuit(cli.cuit); setDireccion(cli.direccion); setCondicionFiscal(cli.condicion_fiscal); setMedioPago(cli.medio_pago); setTelefono(cli.telefono); }} style={{ flex: 1, background: '#f1f5f9', color: '#1e3a8a', border: 'none', padding: '8px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>✏️ Modificar</button>
                      <button onClick={() => eliminarClienteDirecto(cli.id)} style={{ background: '#fef2f2', color: '#dc2626', border: 'none', padding: '8px 12px', borderRadius: '6px', fontWeight: 'bold', cursor: 'pointer' }}>🗑️</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* VISTA 3: HISTORIAL DE PEDIDOS POR FECHAS */}
        {vistaActual === 'historial' && (
          <div>
            <div style={{ background: '#fff', padding: '25px 30px', borderRadius: '16px', border: '1px solid #e2e8f0', marginBottom: '25px' }}>
              <h2 style={{ color: '#0f172a', margin: '0 0 4px 0', fontSize: '24px', fontWeight: '800' }}>Historial de Órdenes & PDFs</h2>
              <p style={{ margin: '0', fontSize: '13px', color: '#64748b' }}>Listado cronológico de pedidos generados en el sistema.</p>
            </div>

            {pedidos.length === 0 ? <p style={{ textAlign: 'center', padding: '40px' }}>No hay pedidos registrados.</p> : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                {pedidos.map(ped => (
                  <div key={ped.id} style={{ background: '#fff', borderRadius: '12px', padding: '20px 25px', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '6px' }}>
                        <h4 style={{ margin: '0', color: '#1e3a8a', fontSize: '18px' }}>Orden #{ped.id} - {ped.razon_social || 'Cliente General'}</h4>
                        <span style={{ background: '#e0f2fe', color: '#0369a1', padding: '3px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 'bold' }}>{ped.estado}</span>
                      </div>
                      <p style={{ margin: '3px 0', fontSize: '13px', color: '#64748b' }}>📅 Fecha: {ped.fecha}</p>
                      <p style={{ margin: '3px 0', fontSize: '13px', color: '#475569' }}>📝 Obs: {ped.observaciones_agente || 'Ninguna'}</p>
                    </div>
                    <div style={{ textAlign: 'right', display: 'flex', alignItems: 'center', gap: '20px' }}>
                      <div>
                        <span style={{ fontSize: '12px', color: '#64748b', display: 'block' }}>Total</span>
                        <span style={{ fontSize: '20px', fontWeight: 'bold', color: '#1e3a8a' }}>${ped.total.toLocaleString('es-AR')}</span>
                      </div>
                      <a href={`http://localhost:8001/documentos_pedidos/orden_pedido_${ped.id}.pdf`} target="_blank" rel="noopener noreferrer" style={{ background: '#dc2626', color: '#fff', padding: '10px 16px', borderRadius: '8px', fontSize: '13px', fontWeight: 'bold', textDecoration: 'none' }}>📄 Ver PDF</a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>

      {/* PANEL LATERAL CARRITO */}
      {carritoAbierto && (
        <div style={{ position: 'fixed', top: 0, right: 0, width: '460px', height: '100vh', background: '#fff', boxShadow: '-10px 0 30px rgba(0,0,0,0.15)', zIndex: 1000, display: 'flex', flexDirection: 'column', boxSizing: 'border-box' }}>
          <div style={{ background: '#1e3a8a', color: '#fff', padding: '20px 25px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: '0', fontSize: '18px' }}>Carrito de Compras & Cierre</h3>
            <button onClick={() => setCarritoAbierto(false)} style={{ background: 'none', border: 'none', color: '#fff', fontSize: '20px', cursor: 'pointer' }}>✕</button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '25px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#0f172a' }}>ARTÍCULOS SELECCIONADOS ({cantidadTotalItems()})</h4>
              {Object.keys(carrito).length === 0 ? <p style={{ color: '#64748b', fontSize: '13px' }}>El carrito está vacío.</p> : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {Object.entries(carrito).map(([idStr, cant]) => {
                    const prod = productos.find(p => p.id === Number(idStr));
                    if (!prod) return null;
                    return (
                      <div key={idStr} style={{ background: '#f8fafc', padding: '12px', borderRadius: '10px', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <strong style={{ fontSize: '13px', display: 'block' }}>{prod.nombre}</strong>
                          <span style={{ fontSize: '11px', color: '#64748b' }}>${prod.precio.toLocaleString('es-AR')} c/u</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <input type="number" min="1" value={cant} onChange={(e) => ajustarCantidadCarrito(prod.id, parseInt(e.target.value) || 0)} style={{ width: '45px', textAlign: 'center', padding: '4px' }} />
                          <button onClick={() => eliminarDelCarrito(prod.id)} style={{ background: 'none', border: 'none', color: '#dc2626', cursor: 'pointer', fontSize: '16px' }} title="Eliminar">🗑️</button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div style={{ background: '#f1f5f9', padding: '15px', borderRadius: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '15px', fontWeight: 'bold' }}>Total Pedido:</span>
              <span style={{ fontSize: '20px', fontWeight: '800', color: '#1e3a8a' }}>${calcularTotal().toLocaleString('es-AR')}</span>
            </div>

            {/* Selector de Cliente o Carga Rápida */}
            <div style={{ background: '#fff', border: '1px solid #cbd5e1', borderRadius: '12px', padding: '16px' }}>
              <h4 style={{ margin: '0 0 12px 0', fontSize: '12px', color: '#1e3a8a', textTransform: 'uppercase' }}>🏢 Datos del Cliente</h4>
              
              <div style={{ marginBottom: '12px' }}>
                <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569' }}>Seleccionar de "Mis Clientes"</label>
                <select value={clienteSeleccionadoId} onChange={seleccionarClienteExistente} style={{ width: '100%', padding: '8px', borderRadius: '8px', border: '1px solid #cbd5e1', marginTop: '4px' }}>
                  <option value="">-- Cargar manualmente o nuevo cliente --</option>
                  {clientes.map(c => <option key={c.id} value={c.id}>{c.razon_social} (CUIT: {c.cuit})</option>)}
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                  <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569' }}>Razón Social / Nombre *</label>
                  <input type="text" value={razonSocial} onChange={(e) => setRazonSocial(e.target.value)} placeholder="Ej. Kiosco Belgrano" style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569' }}>CUIT / DNI *</label>
                    <input type="text" value={cuit} onChange={(e) => setCuit(e.target.value)} placeholder="Ej. 30-7123" style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569' }}>Teléfono</label>
                    <input type="text" value={telefono} onChange={(e) => setTelefono(e.target.value)} placeholder="Ej. 115566" style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} />
                  </div>
                </div>
                <div>
                  <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569' }}>Dirección de Entrega *</label>
                  <input type="text" value={direccion} onChange={(e) => setDireccion(e.target.value)} placeholder="Ej. Av. San Martín 1420" style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} />
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569' }}>Condición Fiscal</label>
                    <select value={condicionFiscal} onChange={(e) => setCondicionFiscal(e.target.value)} style={{ width: '100%', padding: '8px' }}>
                      <option>Responsable Inscripto</option>
                      <option>Monotributo</option>
                      <option>Consumidor Final</option>
                    </select>
                  </div>
                  <div>
                    <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569' }}>Medio de Pago</label>
                    <select value={medioPago} onChange={(e) => setMedioPago(e.target.value)} style={{ width: '100%', padding: '8px' }}>
                      <option>Efectivo contra entrega</option>
                      <option>Transferencia Bancaria</option>
                      <option>Cuenta Corriente 30 días</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#475569', marginBottom: '6px' }}>Observaciones del Pedido (Opcional)</label>
              <textarea value={observaciones} onChange={(e) => setObservaciones(e.target.value)} placeholder="Horarios de descarga..." rows={2} style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid #cbd5e1', boxSizing: 'border-box' }} />
            </div>
          </div>

          <div style={{ padding: '20px 25px', background: '#f8fafc', borderTop: '1px solid #e2e8f0' }}>
            <button onClick={enviarPedido} style={{ width: '100%', padding: '14px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '12px', fontSize: '15px', fontWeight: 'bold', cursor: 'pointer' }}>✅ Confirmar y Generar PDF</button>
          </div>
        </div>
      )}

    </div>
  );
}