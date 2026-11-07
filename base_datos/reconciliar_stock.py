import sqlite3
from pathlib import Path

RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "api" / "distribuidora.db"

def reconciliar():
    conexion = sqlite3.connect(RUTA_DB)
    cursor = conexion.cursor()

    print("🔄 Recalculando stock reservado desde pedidos pendientes...")

    # 1. Resetear stock_reservado a 0
    cursor.execute("UPDATE productos SET stock_reservado = 0")
    
    # 2. Sumar cantidades de pedidos en RECIBIDO o VALIDADO
    cursor.execute("SELECT id FROM pedidos WHERE estado IN ('RECIBIDO', 'VALIDADO')")
    pedidos = cursor.fetchall()
    
    for p in pedidos:
        cursor.execute("SELECT producto_id, cantidad FROM detalle_pedidos WHERE pedido_id = ?", (p[0],))
        for d in cursor.fetchall():
            cursor.execute("UPDATE productos SET stock_reservado = stock_reservado + ? WHERE id = ?", (d[1], d[0]))

    conexion.commit()
    
    # 3. Mostrar resumen
    cursor.execute("SELECT id, codigo, nombre, stock_fisico, stock_reservado FROM productos ORDER BY stock_reservado DESC LIMIT 5")
    print("\n📦 Top 5 productos con más stock reservado:")
    for row in cursor.fetchall():
        print(f"   - {row[1]} ({row[2]}): Físico {row[3]}, Reservado {row[4]}")
    
    cursor.execute("SELECT SUM(stock_reservado) FROM productos")
    total = cursor.fetchone()[0]
    print(f"\n📊 Total de unidades reservadas: {total}")
    
    conexion.close()
    print("✅ Reconciliación completada.")

if __name__ == "__main__":
    reconciliar()