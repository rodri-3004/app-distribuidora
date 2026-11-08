import sqlite3
from pathlib import Path
import bcrypt

RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "api" / "distribuidora.db"

def crear_agentes():
    conexion = sqlite3.connect(RUTA_DB)
    cursor = conexion.cursor()

    # 1. Limpieza: Borramos los agentes viejos (los 5 originales) para evitar duplicados
    # Solo borramos los que tengan rol 'agente' (no tocamos al simulador que tiene rol 'admin')
    emails_viejos = [
        "supervisor@distribuidora.com",
        "recepcionista@distribuidora.com",
        "facturador@distribuidora.com",
        "stock@distribuidora.com",
        "planificador@distribuidora.com"
    ]
    
    print("🧹 Limpiando agentes antiguos...")
    for email in emails_viejos:
        cursor.execute("DELETE FROM usuarios WHERE email = ? AND rol = 'agente'", (email,))
    conexion.commit()
    print("✅ Limpieza completada.\n")

    # 2. Lista completa de los 13 agentes del harness (con sus claves exactas)
    agentes = [
        {"nombre": "Supervisor", "email": "supervisor@distribuidora.com", "clave": "Super123!", "rol": "agente"},
        {"nombre": "Recepcionista", "email": "recepcionista@distribuidora.com", "clave": "Recepcion123!", "rol": "agente"},
        {"nombre": "ValidadorPrecios", "email": "validador_precios@distribuidora.com", "clave": "Precios123!", "rol": "agente"},
        {"nombre": "ValidadorCredito", "email": "validador_credito@distribuidora.com", "clave": "Credito123!", "rol": "agente"},
        {"nombre": "Preparador", "email": "preparador@distribuidora.com", "clave": "Preparador123!", "rol": "agente"},
        {"nombre": "Facturador", "email": "facturador@distribuidora.com", "clave": "Factura123!", "rol": "agente"},
        {"nombre": "Planificador", "email": "planificador@distribuidora.com", "clave": "Plan123!", "rol": "agente"},
        {"nombre": "Auditor", "email": "auditor@distribuidora.com", "clave": "Auditor123!", "rol": "agente"},
        {"nombre": "Registro", "email": "registro@distribuidora.com", "clave": "Registro123!", "rol": "agente"},
        {"nombre": "GestorStock", "email": "stock@distribuidora.com", "clave": "Stock123!", "rol": "agente"},
        {"nombre": "GestorPrecios", "email": "gestor_precios@distribuidora.com", "clave": "GestorPrecios123!", "rol": "agente"},
        {"nombre": "Reposicion", "email": "reposicion@distribuidora.com", "clave": "Reposicion123!", "rol": "agente"},
        # El simulador ya existe (creado por crear_simulador.py), pero nos aseguramos de que esté
        {"nombre": "Simulador", "email": "simulador@distribuidora.com", "clave": "Simulador123!", "rol": "admin"},
    ]

    print("🔄 Creando las 13 identidades de los agentes...\n")

    for ag in agentes:
        # Encriptamos la clave con bcrypt
        clave_hash = bcrypt.hashpw(ag["clave"].encode('utf-8')[:72], bcrypt.gensalt()).decode('utf-8')
        try:
            cursor.execute("SELECT id FROM usuarios WHERE email = ?", (ag["email"],))
            if cursor.fetchone():
                print(f"⚠️  {ag['nombre']:<18} ya existe. (Saltando creación)")
                continue
                
            cursor.execute("""
                INSERT INTO usuarios (nombre, apellido, email, usuario, clave_hash, rol, verificado)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, (ag["nombre"], "Paseo", ag["email"], ag["email"].split("@")[0], clave_hash, ag["rol"]))
            print(f"✅ {ag['nombre']:<18} creado (Email: {ag['email']:<35} | Clave: {ag['clave']})")
        except Exception as e:
            print(f"❌ Error creando {ag['nombre']}: {e}")

    conexion.commit()
    conexion.close()
    print("\n🎉 Proceso finalizado. Todas las identidades fueron verificadas/creadas.")

if __name__ == "__main__":
    crear_agentes()