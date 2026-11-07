import sqlite3
from pathlib import Path

RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "api" / "distribuidora.db"

def resetear():
    conexion = sqlite3.connect(RUTA_DB)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()

    print("🔄 Buscando pedidos en estado CERRADO o ENTREGADO...")

    # Buscamos los pedidos que ya fueron entregados/cerrados
    cursor.execute("SELECT id, fecha FROM pedidos WHERE estado IN ('CERRADO', 'ENTREGADO')")
    pedidos = cursor.fetchall()

    if not pedidos:
        print("✅ No hay pedidos entregados para resetear.")
        conexion.close()
        return

    print(f"🔧 Reseteando {len(pedidos)} pedidos a estado 'RECIBIDO' (Pendiente)...")

    for ped in pedidos:
        pedido_id = ped['id']
        fecha_original = ped['fecha']

        # 1. Devolver el stock físico (porque se había descontado en la simulación)
        cursor.execute("SELECT producto_id, cantidad FROM detalle_pedidos WHERE pedido_id = ?", (pedido_id,))
        detalles = cursor.fetchall()
        for det in detalles:
            cursor.execute("UPDATE productos SET stock_fisico = stock_fisico + ? WHERE id = ?", (det['cantidad'], det['producto_id']))

        # 2. Cambiar el estado del pedido
        cursor.execute("UPDATE pedidos SET estado = 'RECIBIDO' WHERE id = ?", (pedido_id,))

        # 3. Borrar el historial viejo y crear el nuevo
        cursor.execute("DELETE FROM pedido_historial_estados WHERE pedido_id = ?", (pedido_id,))
        cursor.execute("""
            INSERT INTO pedido_historial_estados (pedido_id, estado_anterior, estado_nuevo, fecha, cambiado_por)
            VALUES (?, NULL, 'RECIBIDO', ?, 'Sistema (Reseteo)')
        """, (pedido_id, fecha_original))

    conexion.commit()
    conexion.close()
    print(f"✅ ¡Se resetearon {len(pedidos)} pedidos al estado 'RECIBIDO' y se devolvió el stock!")

if __name__ == "__main__":
    resetear()