import sqlite3
from pathlib import Path

RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "api" / "distribuidora.db"

def crear_tabla():
    conexion = sqlite3.connect(RUTA_DB)
    cursor = conexion.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alertas_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            stock_actual INTEGER NOT NULL,
            fecha_generacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            estado TEXT NOT NULL DEFAULT 'PENDIENTE' CHECK (estado IN ('PENDIENTE', 'REVISADA', 'RESUELTA')),
            FOREIGN KEY (producto_id) REFERENCES productos (id)
        )
    """)
    
    conexion.commit()
    conexion.close()
    print("✅ Tabla 'alertas_stock' creada o verificada con éxito.")

if __name__ == "__main__":
    crear_tabla()