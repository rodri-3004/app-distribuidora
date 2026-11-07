import sqlite3
from pathlib import Path

# Buscamos la base de datos en las ubicaciones posibles
RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "api" / "distribuidora.db"

def migrar():
    if not RUTA_DB.exists():
        print(f"❌ No se encontró la base de datos en {RUTA_DB}")
        return

    conexion = sqlite3.connect(RUTA_DB)
    cursor = conexion.cursor()

    print(f"🔄 Conectado a la base de datos: {RUTA_DB.name}")

    # 1. Crear la tabla de historial de estados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedido_historial_estados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL,
            estado_anterior TEXT,
            estado_nuevo TEXT NOT NULL,
            fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            cambiado_por TEXT NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos (id) ON DELETE CASCADE
        )
    """)
    print("✅ Tabla 'pedido_historial_estados' verificada/creada.")

    # 2. Verificar si necesitamos la columna 'estado_anterior' en pedidos (opcional, para más adelante)
    cursor.execute("PRAGMA table_info(pedidos)")
    columnas = [col[1] for col in cursor.fetchall()]
    
    if "estado_anterior" not in columnas:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN estado_anterior TEXT")
        print("✅ Columna 'estado_anterior' agregada a la tabla 'pedidos'.")
    else:
        print("ℹ️ La columna 'estado_anterior' ya existe en 'pedidos'.")

    # 3. Insertar un registro inicial para los pedidos que ya existen (para que no queden sin historial)
    cursor.execute("SELECT id, estado, fecha FROM pedidos")
    pedidos_existentes = cursor.fetchall()
    
    if pedidos_existentes:
        print(f"🔄 Generando historial inicial para {len(pedidos_existentes)} pedidos existentes...")
        for p in pedidos_existentes:
            pedido_id, estado_actual, fecha_original = p
            # Verificamos si ya tiene historial para no duplicar si corremos el script dos veces
            cursor.execute("SELECT id FROM pedido_historial_estados WHERE pedido_id = ?", (pedido_id,))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO pedido_historial_estados (pedido_id, estado_anterior, estado_nuevo, fecha, cambiado_por)
                    VALUES (?, NULL, ?, ?, 'Sistema (Migración)')
                """, (pedido_id, estado_actual, fecha_original))
        print("✅ Historial inicial generado.")

    conexion.commit()
    conexion.close()
    print("🎉 ¡Migración completada con éxito! Ya podés pasar al Paso 2 (API).")

if __name__ == "__main__":
    migrar()