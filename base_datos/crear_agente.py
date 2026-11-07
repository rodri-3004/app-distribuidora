import sqlite3
from pathlib import Path
import bcrypt

RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "api" / "distribuidora.db"

def crear_agente():
    conexion = sqlite3.connect(RUTA_DB)
    cursor = conexion.cursor()

    email = "agente@distribuidora.com"
    clave = "ClaveAgente123!"
    
    # Hasheamos la clave con bcrypt
    clave_hash = bcrypt.hashpw(clave.encode('utf-8')[:72], bcrypt.gensalt()).decode('utf-8')

    try:
        cursor.execute("SELECT id FROM usuarios WHERE email = ?", (email,))
        if cursor.fetchone():
            print("El agente ya existe en la base de datos.")
            return

        # Le damos rol 'admin' para que pueda hacer todo (luego lo cambiamos a 'agente' si querés)
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellido, email, usuario, clave_hash, rol, verificado)
            VALUES (?, ?, ?, ?, ?, 'admin', 1)
        """, ("Agente", "Paseo", email, "agente_paseo", clave_hash))
        
        conexion.commit()
        print("✅ Agente Paseo creado con éxito.")
        print(f"   Email: {email}")
        print(f"   Clave: {clave}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conexion.close()

if __name__ == "__main__":
    crear_agente()