import sqlite3
from pathlib import Path

RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "api" / "distribuidora.db"

def migrar():
    conexion = sqlite3.connect(RUTA_DB)
    cursor = conexion.cursor()
    
    # Verificamos si ya acepta el rol 'agente'
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='usuarios'")
    sql = cursor.fetchone()[0]
    if "'agente'" in sql:
        print("✅ La tabla ya acepta el rol 'agente'.")
        conexion.close()
        return
        
    print("🔄 Recreando tabla usuarios para agregar el rol 'agente'...")
    conexion.execute("PRAGMA foreign_keys = OFF")
    
    # 1. Creamos la tabla nueva con el CHECK actualizado
    cursor.execute("""
        CREATE TABLE usuarios_nueva (
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
            rol TEXT NOT NULL DEFAULT 'cliente' CHECK (rol IN ('admin', 'cliente', 'agente')),
            cliente_id INTEGER,
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    """)
    
    # 2. Copiamos los datos
    cursor.execute("INSERT INTO usuarios_nueva SELECT * FROM usuarios")
    
    # 3. Borramos la vieja y renombramos la nueva
    cursor.execute("DROP TABLE usuarios")
    cursor.execute("ALTER TABLE usuarios_nueva RENAME TO usuarios")
    
    conexion.commit()
    conexion.execute("PRAGMA foreign_keys = ON")
    conexion.close()
    print("✅ Tabla 'usuarios' actualizada con el rol 'agente'.")

if __name__ == "__main__":
    migrar()