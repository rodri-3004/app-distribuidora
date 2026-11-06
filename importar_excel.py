import sqlite3
from pathlib import Path
import pandas as pd

# Rutas seguras dentro del proyecto
BASE_DIR = Path(__file__).parent
RUTA_DB = BASE_DIR / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = BASE_DIR / "base_datos" / "distribuidora.db"

RUTA_CLIENTES = BASE_DIR / "clientes.xlsx"
RUTA_PRODUCTOS = BASE_DIR / "productos.xlsx"

def asegurar_columnas(cursor):
    """Verifica y agrega columnas faltantes en tablas existentes sin borrar datos"""
    # Asegurar tabla clientes y sus columnas
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            razon_social TEXT NOT NULL,
            cuit TEXT UNIQUE NOT NULL,
            direccion_entrega TEXT NOT NULL,
            telefono TEXT DEFAULT '',
            condicion_fiscal TEXT DEFAULT 'Responsable Inscripto',
            medio_pago TEXT DEFAULT 'Efectivo contra entrega',
            limite_credito REAL DEFAULT 0.0,
            saldo_actual REAL DEFAULT 0.0,
            estado TEXT DEFAULT 'ACTIVO',
            usuario_dueno TEXT DEFAULT 'admin'
        )
    """)
    
    # Si la tabla ya existía de antes, verificamos si falta la columna usuario_dueno
    cursor.execute("PRAGMA table_info(clientes)")
    columnas_clientes = [col["name"] for col in cursor.fetchall()]
    if "usuario_dueno" not in columnas_clientes:
        cursor.execute("ALTER TABLE clientes ADD COLUMN usuario_dueno TEXT DEFAULT 'admin'")

    # Asegurar tabla productos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            categoria TEXT NOT NULL,
            precio REAL NOT NULL,
            stock_fisico INTEGER DEFAULT 0,
            stock_reservado INTEGER DEFAULT 0,
            peso_kg REAL DEFAULT 0.0,
            volumen_dm3 REAL DEFAULT 0.0,
            imagen_url TEXT DEFAULT 'default.png',
            activo INTEGER DEFAULT 1
        )
    """)

def importar_planillas():
    print(f"📂 Usando base de datos en: {RUTA_DB}")
    RUTA_DB.parent.mkdir(parents=True, exist_ok=True)
    
    conexion = sqlite3.connect(RUTA_DB)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()

    # Asegurar tablas y columnas antes de operar
    asegurar_columnas(cursor)
    conexion.commit()

    # Desactivar temporalmente claves foráneas para importación limpia
    cursor.execute("PRAGMA foreign_keys = OFF;")

    # 1. IMPORTAR / ACTUALIZAR PRODUCTOS DESDE productos.xlsx
    if RUTA_PRODUCTOS.exists():
        print("📦 Procesando 'productos.xlsx'...")
        df_productos = pd.read_excel(RUTA_PRODUCTOS, sheet_name="productos")
        
        actualizados = 0
        for _, row in df_productos.iterrows():
            codigo = str(row['codigo'])
            nombre = str(row['nombre'])
            categoria = str(row['categoria'])
            precio = float(row['precio'])
            stock_inicial = int(row['stock_inicial'])
            peso_kg = float(row['peso_kg'])
            volumen_dm3 = float(row['volumen_dm3'])
            imagen_url = str(row.get('imagen_url', 'default.png'))
            activo = int(row['activo'])

            cursor.execute("SELECT id FROM productos WHERE codigo = ?", (codigo,))
            prod_db = cursor.fetchone()

            if prod_db:
                cursor.execute("""
                    UPDATE productos 
                    SET nombre = ?, categoria = ?, precio = ?, stock_fisico = ?, peso_kg = ?, volumen_dm3 = ?, imagen_url = ?, activo = ?
                    WHERE codigo = ?
                """, (nombre, categoria, precio, stock_inicial, peso_kg, volumen_dm3, imagen_url, activo, codigo))
            else:
                cursor.execute("""
                    INSERT INTO productos (codigo, nombre, categoria, precio, stock_fisico, stock_reservado, peso_kg, volumen_dm3, imagen_url, activo)
                    VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                """, (codigo, nombre, categoria, precio, stock_inicial, peso_kg, volumen_dm3, imagen_url, activo))
            actualizados += 1
        print(f"✅ Productos procesados con éxito: {actualizados}")
    else:
        print("⚠️ No se encontró el archivo 'productos.xlsx'.")

    # 2. IMPORTAR / ACTUALIZAR CLIENTES DESDE clientes.xlsx
    if RUTA_CLIENTES.exists():
        print("👥 Procesando 'clientes.xlsx'...")
        df_clientes = pd.read_excel(RUTA_CLIENTES, sheet_name="clientes")

        def limpiar_telefono(val):
            if pd.isna(val):
                return ""
            try:
                return str(int(float(val)))
            except:
                return str(val)

        clientes_procesados = 0
        for _, row in df_clientes.iterrows():
            cuit = str(row['cuit'])
            razon_social = str(row['razon_social'])
            direccion = str(row['direccion_entrega'])
            telefono = limpiar_telefono(row.get('telefono', ''))
            condicion_fiscal = str(row.get('condicion_fiscal', 'Responsable Inscripto'))
            medio_pago = str(row.get('medio_pago', 'Efectivo contra entrega'))
            limite_credito = float(row.get('limite_credito', 0.0))
            estado = str(row.get('estado', 'ACTIVO'))
            saldo_inicial = float(row.get('saldo_inicial', 0.0))
            usuario_dueno = str(row.get('usuario_dueno', 'admin'))

            cursor.execute("SELECT id FROM clientes WHERE cuit = ?", (cuit,))
            cli_db = cursor.fetchone()

            if cli_db:
                cursor.execute("""
                    UPDATE clientes 
                    SET razon_social = ?, direccion_entrega = ?, telefono = ?, condicion_fiscal = ?, medio_pago = ?, limite_credito = ?, estado = ?, saldo_actual = ?, usuario_dueno = ?
                    WHERE cuit = ?
                """, (razon_social, direccion, telefono, condicion_fiscal, medio_pago, limite_credito, estado, saldo_inicial, usuario_dueno, cuit))
            else:
                cursor.execute("""
                    INSERT INTO clientes (razon_social, cuit, direccion_entrega, telefono, condicion_fiscal, medio_pago, limite_credito, saldo_actual, estado, usuario_dueno)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (razon_social, cuit, direccion, telefono, condicion_fiscal, medio_pago, limite_credito, saldo_inicial, estado, usuario_dueno))
            clientes_procesados += 1
        print(f"✅ Clientes procesados con éxito: {clientes_procesados}")
    else:
        print("⚠️ No se encontró el archivo 'clientes.xlsx'.")

    cursor.execute("PRAGMA foreign_keys = ON;")
    conexion.commit()
    conexion.close()
    print("🎉 ¡Sincronización masiva desde Excel completada con éxito!")

if __name__ == "__main__":
    importar_planillas()