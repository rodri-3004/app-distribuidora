import sqlite3
from pathlib import Path

RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent / "base_datos" / "distribuidora.db"

def limpiar():
    conexion = sqlite3.connect(RUTA_DB)
    cursor = conexion.cursor()

    print("🧹 Limpiando base de datos y reasignando clientes...")

    # 1. Borrar todos los pedidos anteriores generados por el script viejo para evitar inconsistencias de stock
    cursor.execute("DELETE FROM detalle_pedidos")
    cursor.execute("DELETE FROM pedidos")

    # 2. Reasignar clientes huérfanos a un usuario válido (ej: 'admin' o 'roberbola')
    cursor.execute("""
        UPDATE clientes 
        SET usuario_dueno = 'admin' 
        WHERE usuario_dueno IN ('prev_norte', 'prev_capital') OR usuario_dueno IS NULL
    """)

    # 3. Resetear stock reservado a 0 y asegurar stock físico real en 500 para todos
    cursor.execute("""
        UPDATE productos 
        SET stock_fisico = 500, stock_reservado = 0 
        WHERE activo = 1
    """)

    conexion.commit()
    conexion.close()
    print("✅ Base de datos limpiada, stock sincronizado y clientes reasignados correctamente.")

if __name__ == "__main__":
    limpiar()