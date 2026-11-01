// frontend/src/App.tsx
import { useState } from 'react';
import { loginUsuario, obtenerProductos } from './services/api';
import './App.css';

function App() {
  const [email, setEmail] = useState('');
  const [clave, setClave] = useState('');
  const [usuarioLogueado, setUsuarioLogueado] = useState<any>(null);
  const [error, setError] = useState('');
  
  const [productos, setProductos] = useState<any[]>([]);
  const [cargandoProductos, setCargandoProductos] = useState(false);

  // Estado para el carrito: { [productoId]: cantidad }
  const [carrito, setCarrito] = useState<{ [key: number]: number }>({});
  const [observaciones, setObservaciones] = useState('');
  const [mensajePedido, setMensajePedido] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      const data = await loginUsuario(email, clave);
      setUsuarioLogueado(data.usuario);
      cargarCatalogo();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const cargarCatalogo = async () => {
    setCargandoProductos(true);
    try {
      const prods = await obtenerProductos();
      setProductos(prods);
    } catch (err: any) {
      console.error(err);
    } finally {
      setCargandoProductos(false);
    }
  };

  const actualizarCantidad = (productoId: number, cantidad: number) => {
    if (cantidad <= 0) {
      const nuevoCarrito = { ...carrito };
      delete nuevoCarrito[productoId];
      setCarrito(nuevoCarrito);
    } else {
      setCarrito({ ...carrito, [productoId]: cantidad });
    }
  };

  const calcularTotal = () => {
    let total = 0;
    for (const [idStr, cantidad] of Object.entries(carrito)) {
      const prod = productos.find(p => p.id === Number(idStr));
      if (prod) {
        total += prod.precio * cantidad;
      }
    }
    return total;
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

    try {
      const response = await fetch("http://127.0.0.1:8001/pedidos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cliente_id: usuarioLogueado.id, // Usamos el ID del usuario logueado como cliente
          observaciones_agente: observaciones || "Pedido web B2B",
          items: items
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Error al procesar el pedido.");
      }

      setMensajePedido(`¡Pedido #${data.pedido_id} creado con éxito! Total: $${data.total_pedido.toLocaleString('es-AR')}`);
      setCarrito({});
      setObservaciones('');
      cargarCatalogo(); // Recargar para ver el stock actualizado
    } catch (err: any) {
      alert(`Error: ${err.message}`);
    }
  };

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '30px', maxWidth: '1000px', margin: '0 auto' }}>
      <h2>B2B Distribuidora - Portal de Clientes</h2>
      
      {!usuarioLogueado ? (
        <div style={{ maxWidth: '400px', margin: '40px auto', background: '#f9fafb', padding: '20px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
          <h3>Acceso al Sistema</h3>
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
            <button type="submit" style={{ padding: '10px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', borderRadius: '4px' }}>
              Ingresar
            </button>
            {error && <p style={{ color: 'red', margin: '0' }}>{error}</p>}
          </form>
        </div>
      ) : (
        <div>
          {/* Cabecera de usuario */}
          <div style={{ background: '#f0fdf4', padding: '15px', border: '1px solid #bbf7d0', borderRadius: '5px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div>
              <h3 style={{ margin: '0 0 5px 0', color: '#166534' }}>¡Bienvenido, {usuarioLogueado.nombre} {usuarioLogueado.apellido}!</h3>
              <p style={{ margin: '0', fontSize: '14px', color: '#374151' }}>Email: {usuarioLogueado.email} | Rol: <strong>{usuarioLogueado.rol}</strong></p>
            </div>
            <button 
              onClick={() => { setUsuarioLogueado(null); setProductos([]); setCarrito({}); }} 
              style={{ padding: '8px 12px', background: '#dc2626', color: '#fff', border: 'none', cursor: 'pointer', borderRadius: '4px' }}
            >
              Cerrar Sesión
            </button>
          </div>

          {mensajePedido && (
            <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', padding: '15px', borderRadius: '5px', marginBottom: '20px', color: '#1e40af', fontWeight: 'bold' }}>
              {mensajePedido}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
            {/* Catálogo de Productos */}
            <div>
              <h3>Catálogo de Productos</h3>
              {cargandoProductos ? (
                <p>Cargando productos...</p>
              ) : (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '15px' }}>
                  {productos.map((prod) => (
                    <div key={prod.id} style={{ border: '1px solid #e5e7eb', borderRadius: '6px', padding: '12px', background: '#fff', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                      <div>
                        <h4 style={{ margin: '0 0 8px 0', color: '#1f2937' }}>{prod.nombre}</h4>
                        <p style={{ margin: '4px 0', fontSize: '15px', fontWeight: 'bold', color: '#2563eb' }}>
                          ${prod.precio.toLocaleString('es-AR')}
                        </p>
                        <p style={{ margin: '4px 0', fontSize: '12px', color: prod.stock_fisico > 0 ? '#059669' : '#dc2626' }}>
                          Stock: <strong>{prod.stock_fisico}</strong>
                        </p>
                      </div>
                      <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span style={{ fontSize: '13px', color: '#4b5563' }}>Cantidad:</span>
                        <input 
                          type="number" 
                          min="0" 
                          max={prod.stock_fisico}
                          value={carrito[prod.id] || ''} 
                          onChange={(e) => actualizarCantidad(prod.id, parseInt(e.target.value) || 0)}
                          style={{ width: '60px' }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Resumen del Pedido / Carrito */}
            <div style={{ background: '#f9fafb', border: '1px solid #e5e7eb', borderRadius: '8px', padding: '15px', height: 'fit-content' }}>
              <h3>Carrito de Pedido</h3>
              {Object.keys(carrito).length === 0 ? (
                <p style={{ color: '#6b7280', fontSize: '14px' }}>El carrito está vacío. Seleccioná cantidades en el catálogo.</p>
              ) : (
                <div>
                  <ul style={{ paddingLeft: '20px', margin: '0 0 15px 0', fontSize: '14px' }}>
                    {Object.entries(carrito).map(([idStr, cant]) => {
                      const prod = productos.find(p => p.id === Number(idStr));
                      if (!prod) return null;
                      return (
                        <li key={idStr} style={{ marginBottom: '8px' }}>
                          {prod.nombre} x <strong>{cant}</strong> (${(prod.precio * cant).toLocaleString('es-AR')})
                        </li>
                      );
                    })}
                  </ul>

                  <div style={{ borderTop: '1px solid #e5e7eb', paddingTop: '10px', marginBottom: '15px' }}>
                    <p style={{ fontSize: '16px', fontWeight: 'bold', margin: '0', display: 'flex', justifyContent: 'space-between' }}>
                      <span>Total:</span>
                      <span style={{ color: '#2563eb' }}>${calcularTotal().toLocaleString('es-AR')}</span>
                    </p>
                  </div>

                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', fontSize: '13px', marginBottom: '5px' }}>Observaciones:</label>
                    <input 
                      type="text" 
                      value={observaciones} 
                      onChange={(e) => setObservaciones(e.target.value)} 
                      placeholder="Ej. Entregar por la mañana" 
                      style={{ width: '100%', padding: '6px', boxSizing: 'border-box', fontSize: '13px' }}
                    />
                  </div>

                  <button 
                    onClick={enviarPedido} 
                    style={{ width: '100%', padding: '10px', background: '#059669', color: '#fff', border: 'none', cursor: 'pointer', borderRadius: '4px', fontWeight: 'bold' }}
                  >
                    Confirmar y Enviar Pedido
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
