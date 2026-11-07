import sqlite3
from pathlib import Path
from datetime import date, timedelta

RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "api" / "distribuidora.db"

def distribuir():
    conexion = sqlite3.connect(RUTA_DB)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()

    print("🔄 Distribuyendo pedidos en fechas de entrega...")

    # 1. Obtener todos los pedidos (solo los que no están CERRADOS ni CANCELADOS)
    cursor.execute("SELECT id FROM pedidos WHERE estado NOT IN ('CERRADO', 'CANCELADO') ORDER BY id ASC")
    pedidos = cursor.fetchall()
    
    if not pedidos:
        print("ℹ️ No hay pedidos para distribuir.")
        conexion.close()
        return

    print(f"📦 Se encontraron {len(pedidos)} pedidos activos.")

    # 2. Distribuir en bloques de 25 pedidos por día
    # Empezamos desde mañana (para no entregar todo hoy)
    fecha_actual = date.today() + timedelta(days=1)
    PEDIDOS_POR_DIA = 25
    contador = 0

    for ped in pedidos:
        # Cada vez que llegamos a 25, pasamos al día siguiente
        if contador > 0 and contador % PEDIDOS_POR_DIA == 0:
            fecha_actual += timedelta(days=1)
        
        cursor.execute("UPDATE pedidos SET fecha_entrega = ? WHERE id = ?", (fecha_actual.isoformat(), ped["id"]))
        contador += 1

    conexion.commit()
    
    # 3. Mostrar resumen de cómo quedaron distribuidos
    cursor.execute("SELECT fecha_entrega, COUNT(*) as cant FROM pedidos WHERE estado NOT IN ('CERRADO', 'CANCELADO') GROUP BY fecha_entrega ORDER BY fecha_entrega ASC")
    print("\n📅 Distribución final:")
    for row in cursor.fetchall():
        print(f"   - {row['fecha_entrega']}: {row['cant']} pedidos")

    conexion.close()
    print("\n✅ Distribución completada.")

if __name__ == "__main__":
    distribuir()