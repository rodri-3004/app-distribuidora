import sqlite3
from pathlib import Path
import bcrypt

RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "api" / "distribuidora.db"

def crear_simulador():
    conexion = sqlite3.connect(RUTA_DB)
    cursor = conexion.cursor()

    email = "simulador@distribuidora.com"
    clave = "Simulador123!"
    clave_hash = bcrypt.hashpw(clave.encode('utf-8')[:72], bcrypt.gensalt()).decode('utf-8')

    try:
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
        if cursor.fetchone():
            print("El simulador ya existe.")
            return

        # Le damos rol 'admin' porque va a hacer de operario y chofer a la vez
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellido, email, usuario, clave_hash, rol, verificado)
            VALUES (?, ?, ?, ?, ?, 'admin', 1)
        """, ("Simulador", "Humano", email, "simulador_humano", clave_hash))
        
        conexion.commit()
        print("✅ Usuario Simulador creado con éxito.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conexion.close()

if __name__ == "__main__":
    crear_simulador()