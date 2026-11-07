import sqlite3
from pathlib import Path
import bcrypt

RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "api" / "distribuidora.db"

def crear_agentes():
    conexion = sqlite3.connect(RUTA_DB)
    cursor = conexion.cursor()

    agentes = [
        {"nombre": "Supervisor", "email": "supervisor@distribuidora.com", "clave": "Super123!", "rol": "agente"},
        {"nombre": "Recepcionista", "email": "recepcionista@distribuidora.com", "clave": "Recepcion123!", "rol": "agente"},
        {"nombre": "Facturador", "email": "facturador@distribuidora.com", "clave": "Factura123!", "rol": "agente"},
        {"nombre": "GestorStock", "email": "stock@distribuidora.com", "clave": "Stock123!", "rol": "agente"},
        {"nombre": "Planificador", "email": "planificador@distribuidora.com", "clave": "Plan123!", "rol": "agente"},
    ]

    for ag in agentes:
        clave_hash = bcrypt.hashpw(ag["clave"].encode('utf-8')[:72], bcrypt.gensalt()).decode('utf-8')
        try:
            cursor.execute("SELECT id FROM usuarios WHERE email = ?", (ag["email"],))
            if cursor.fetchone():
                print(f"⚠️ El agente {ag['nombre']} ya existe.")
                continue
                
            cursor.execute("""
                INSERT INTO usuarios (nombre, apellido, email, usuario, clave_hash, rol, verificado)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (ag["nombre"], "Paseo", ag["email"], ag["email"].split("@")[0], clave_hash, ag["rol"]))
            print(f"✅ Agente {ag['nombre']} creado (Email: {ag['email']})")
        except Exception as e:
            print(f"❌ Error creando {ag['nombre']}: {e}")

    conexion.commit()
    conexion.close()

if __name__ == "__main__":
    crear_agentes()