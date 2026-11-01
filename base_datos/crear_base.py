import sqlite3
from pathlib import Path

# La base se guarda al lado de este archivo
RUTA_DB = Path(__file__).parent / "distribuidora.db"

def conectar():
    conexion = sqlite3.connect(RUTA_DB)
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion

TABLAS = [
    # 1. Tabla de Clientes (Globales / Cuentas Corrientes)
    """
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        razon_social TEXT NOT NULL,
        cuit TEXT NOT NULL UNIQUE,
        direccion_entrega TEXT,
        limite_credito REAL NOT NULL DEFAULT 0 CHECK (limite_credito >= 0),
        saldo_actual REAL NOT NULL DEFAULT 0,
        estado TEXT NOT NULL DEFAULT 'ACTIVO'
            CHECK (estado IN ('ACTIVO', 'BLOQUEADO_POR_DEUDA'))
    )
    """,
    # 2. Tabla de Usuarios (Actualizada con campos de registro, Google OAuth y verificación)
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        apellido TEXT,
        usuario TEXT UNIQUE,
        email TEXT UNIQUE NOT NULL,
        dni_cuil TEXT UNIQUE,
        clave_hash TEXT,
        google_id TEXT UNIQUE,
        verificado INTEGER DEFAULT 0,
        token_verificacion TEXT,
        rol TEXT NOT NULL DEFAULT 'cliente' CHECK (rol IN ('admin', 'cliente')),
        cliente_id INTEGER,
        FOREIGN KEY (cliente_id) REFERENCES clientes (id)
    )
    """,
    # 3. Tabla de Clientes Propios (Cartera comercial que gestiona cada usuario)
    """
    CREATE TABLE IF NOT EXISTS clientes_propios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL,
        nombre_razon_social TEXT NOT NULL,
        direccion TEXT NOT NULL,
        cuit_dni TEXT NOT NULL,
        tipo_condicion TEXT NOT NULL,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
    )
    """,
    # 4. Tabla de Productos
    """
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        precio REAL NOT NULL CHECK (precio > 0),
        stock_fisico INTEGER NOT NULL DEFAULT 0 CHECK (stock_fisico >= 0),
        stock_reservado INTEGER NOT NULL DEFAULT 0 CHECK (stock_reservado >= 0),
        peso_kg REAL CHECK (peso_kg IS NULL OR peso_kg > 0),
        volumen_dm3 REAL CHECK (volumen_dm3 IS NULL OR volumen_dm3 > 0),
        imagen_url TEXT DEFAULT 'default.png',
        activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
        CHECK (stock_reservado <= stock_fisico)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS precios_historial (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER NOT NULL,
        precio_anterior REAL NOT NULL CHECK (precio_anterior > 0),
        precio_nuevo REAL NOT NULL CHECK (precio_nuevo > 0),
        motivo TEXT,
        origen TEXT NOT NULL CHECK (origen IN ('ERP', 'AGENTE')),
        fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producto_id) REFERENCES productos (id)
    )
    """,
    # 5. Tabla de Pedidos (Actualizada con usuario_id y pdf_path para subagentes)
    """
    CREATE TABLE IF NOT EXISTS pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        usuario_id INTEGER,
        fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        estado TEXT NOT NULL DEFAULT 'RECIBIDO' 
            CHECK (estado IN ('RECIBIDO', 'VALIDADO', 'PREPARADO', 'FACTURADO', 'ARMADO', 'CARGADO', 'EN_REPARTO', 'ENTREGADO', 'CERRADO', 'EXCEPCION')),
        total REAL NOT NULL DEFAULT 0 CHECK (total >= 0),
        mail_id TEXT,
        observaciones_agente TEXT,
        pdf_path TEXT,
        FOREIGN KEY (cliente_id) REFERENCES clientes (id),
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS detalle_pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL,
        producto_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL CHECK (cantidad > 0),
        precio_unitario REAL NOT NULL CHECK (precio_unitario > 0),
        FOREIGN KEY (pedido_id) REFERENCES pedidos (id),
        FOREIGN KEY (producto_id) REFERENCES productos (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS movimientos_cuenta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        tipo TEXT NOT NULL CHECK (tipo IN ('PEDIDO', 'PAGO', 'AJUSTE')),
        monto REAL NOT NULL,
        pedido_id INTEGER,
        FOREIGN KEY (cliente_id) REFERENCES clientes (id),
        FOREIGN KEY (pedido_id) REFERENCES pedidos (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS facturas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL,
        numero TEXT NOT NULL UNIQUE,
        subtotal REAL NOT NULL CHECK (subtotal >= 0),
        impuestos REAL NOT NULL CHECK (impuestos >= 0),
        total REAL NOT NULL CHECK (total >= 0),
        estado TEXT NOT NULL DEFAULT 'BORRADOR' CHECK (estado IN ('BORRADOR', 'EMITIDA', 'ANULADA')),
        FOREIGN KEY (pedido_id) REFERENCES pedidos (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS armados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL,
        factura_id INTEGER NOT NULL,
        bultos INTEGER NOT NULL CHECK (bultos > 0),
        resultado TEXT NOT NULL DEFAULT 'OK' CHECK (resultado IN ('OK', 'DIFERENCIAS')),
        detalle_diferencias TEXT,
        FOREIGN KEY (pedido_id) REFERENCES pedidos (id),
        FOREIGN KEY (factura_id) REFERENCES facturas (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS camiones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patente TEXT NOT NULL UNIQUE,
        capacidad_kg REAL NOT NULL CHECK (capacidad_kg > 0),
        capacidad_vol REAL NOT NULL CHECK (capacidad_vol > 0)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rutas_paradas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        camion_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        pedido_id INTEGER NOT NULL,
        orden_carga INTEGER NOT NULL,
        orden_entrega INTEGER NOT NULL,
        FOREIGN KEY (camion_id) REFERENCES camiones (id),
        FOREIGN KEY (pedido_id) REFERENCES pedidos (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS entregas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parada_id INTEGER NOT NULL,
        hora TEXT,
        receptor TEXT,
        resultado TEXT NOT NULL CHECK (resultado IN ('ENTREGADO', 'RECHAZADO', 'AUSENTE')),
        incidencia TEXT,
        comprobante TEXT,
        FOREIGN KEY (parada_id) REFERENCES rutas_paradas (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS eventos_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        agente TEXT NOT NULL,
        pedido_id INTEGER,
        accion TEXT NOT NULL,
        entrada_json TEXT,
        salida_json TEXT,
        evidencia TEXT,
        FOREIGN KEY (pedido_id) REFERENCES pedidos (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS excepciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pedido_id INTEGER NOT NULL,
        tipo TEXT NOT NULL,
        motivo TEXT NOT NULL,
        estado TEXT NOT NULL DEFAULT 'ABIERTA' CHECK (estado IN ('ABIERTA', 'RESUELTA')),
        resuelta_por TEXT,
        fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (pedido_id) REFERENCES pedidos (id)
    )
    """
]

def insertar_datos_prueba(conexion):
    cursor = conexion.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM clientes")
    if cursor.fetchone()[0] == 0:
        clientes_prueba = [
            ("Limpieza Total S.A.", "30-71112222-3", "Av. Mitre 1234, Vicente López", 150000.0, 0.0, "ACTIVO"),
            ("Supermercados del Sol", "30-65554444-1", "Corrientes 500, CABA", 50000.0, 45000.0, "ACTIVO"),
            ("Hotel de la Costa", "30-50001111-9", "Del Libertador 800, San Isidro", 100000.0, 110000.0, "BLOQUEADO_POR_DEUDA"),
            ("Consorcio Edificio Torre", "30-99998888-4", "Maipú 450, Vicente López", 80000.0, 0.0, "ACTIVO")
        ]
        cursor.executemany("""
            INSERT INTO clientes (razon_social, cuit, direccion_entrega, limite_credito, saldo_actual, estado)
            VALUES (?, ?, ?, ?, ?, ?)
        """, clientes_prueba)

        productos_prueba = [
            ("LIM-001", "Lavandina Concentrada 1L", 1200.0, 100, 0, 1.1, 1.0, "lavandina.png", 1),
            ("LIM-002", "Detergente Desengrasante 500ml", 950.0, 150, 0, 0.6, 0.5, "detergente.png", 1),
            ("LIM-003", "Desinfectante de Pisos Pino 5L", 4500.0, 50, 0, 5.2, 5.0, "desinfectante.png", 1),
            ("LIM-004", "Jabón Líquido para Ropa 3L", 3800.0, 80, 0, 3.2, 3.0, None, 1),
            ("LIM-005", "Multiuso Gatillo 750ml", 1400.0, 120, 0, 0.8, 0.7, None, 1),
            ("LIM-006", "Esponja Multiuso (Paquete x3)", 600.0, 200, 0, 0.1, 0.2, None, 1),
            ("LIM-007", "Guantes de Látex (Talle M)", 1100.0, 90, 0, 0.2, 0.1, None, 1),
            ("LIM-008", "Papel Higiénico Hoja Doble x4", 1800.0, 130, 0, 0.5, 1.2, None, 1)
        ]
        cursor.executemany("""
            INSERT INTO productos (codigo, nombre, precio, stock_fisico, stock_reservado, peso_kg, volumen_dm3, imagen_url, activo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, productos_prueba)
        
        conexion.commit()
        print("Datos de prueba insertados con éxito.")

def crear_tablas():
    conexion = conectar()
    for sentencia in TABLAS:
        conexion.execute(sentencia)
    
    insertar_datos_prueba(conexion)
    conexion.close()
    print("Base de datos estructurada por completo con tablas de usuarios, clientes propios y trazabilidad.")

if __name__ == "__main__":
    crear_tablas()