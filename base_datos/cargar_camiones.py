import sqlite3
from pathlib import Path

RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "api" / "distribuidora.db"

def cargar():
    conexion = sqlite3.connect(RUTA_DB)
    cursor = conexion.cursor()

    camiones = [
        ("AB123CD", 1000.0, 10.0),
        ("EF456GH", 1500.0, 15.0),
        ("IJ789KL", 800.0, 8.0)
    ]

    for patente, kg, vol in camiones:
        cursor.execute("INSERT OR IGNORE INTO camiones (patente, capacidad_kg, capacidad_vol) VALUES (?, ?, ?)", (patente, kg, vol))
    
    conexion.commit()
    
    cursor.execute("SELECT id, patente, capacidad_kg, capacidad_vol FROM camiones")
    print("✅ Camiones cargados:")
    for row in cursor.fetchall():
        print(f"   - ID {row[0]}: {row[1]} ({row[2]} kg / {row[3]} m³)")
    
    conexion.close()

if __name__ == "__main__":
    cargar()