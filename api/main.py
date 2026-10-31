from fastapi import FastAPI, HTTPException
import sqlite3
from pathlib import Path
from pydantic import BaseModel       # <-- Arriba con los imports
from typing import List, Optional    # <-- Arriba con los imports

app = FastAPI(
    title="API Distribuidora de Limpieza",
    version="1.0",
    description="API de la plataforma piloto para gestión de pedidos, stock y clientes."
)

RUTA_DB = Path(__file__).parent.parent / "base_datos" / "distribuidora.db"

def obtener_conexion():
    if not RUTA_DB.exists():
        raise HTTPException(status_code=500, detail="La base de datos no existe. Ejecute crear_base.py primero.")
    conexion = sqlite3.connect(RUTA_DB)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion

@app.get("/")
def inicio():
    return {"mensaje": "API de la Distribuidora funcionando correctamente", "documentacion": "/docs"}

@app.get("/productos")
def listar_productos():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM productos WHERE activo = 1")
    productos = [dict(fila) for fila in cursor.fetchall()]
    conexion.close()
    return productos

@app.get("/clientes")
def listar_clientes():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM clientes")
    clientes = [dict(fila) for fila in cursor.fetchall()]
    conexion.close()
    return clientes


# ==========================================
# NUEVO: Modelos y Endpoint de Pedidos abajo
# ==========================================

class DetalleItem(BaseModel):
    producto_id: int
    cantidad: int

class PedidoCreate(BaseModel):
    cliente_id: int
    observaciones_agente: Optional[str] = None
    items: List[DetalleItem]

@app.post("/pedidos")
def crear_pedido(pedido: PedidoCreate):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        cursor.execute("SELECT * FROM clientes WHERE id = ?", (pedido.cliente_id,))
        cliente = cursor.fetchone()
        if not cliente:
            raise HTTPException(status_code=404, detail="El cliente especificado no existe.")
        
        if cliente["estado"] == "BLOQUEADO_POR_DEUDA":
            raise HTTPException(status_code=400, detail="Operación rechazada: El cliente se encuentra bloqueado por deuda.")

        total_pedido = 0.0
        detalles_a_procesar = []

        for item in pedido.items:
            cursor.execute("SELECT * FROM productos WHERE id = ? AND activo = 1", (item.producto_id,))
            prod = cursor.fetchone()
            if not prod:
                raise HTTPException(status_code=404, detail=f"Producto ID {item.producto_id} no encontrado o inactivo.")
            
            if prod["stock_fisico"] < item.cantidad:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Stock insuficiente para '{prod['nombre']}'. Disponible: {prod['stock_fisico']}, solicitado: {item.cantidad}."
                )
            
            subtotal = prod["precio"] * item.cantidad
            total_pedido += subtotal
            detalles_a_procesar.append({
                "producto_id": item.producto_id,
                "cantidad": item.cantidad,
                "precio_unitario": prod["precio"]
            })

        credito_disponible = cliente["limite_credito"] - cliente["saldo_actual"]
        if total_pedido > credito_disponible:
            raise HTTPException(
                status_code=400,
                detail=f"Crédito insuficiente. Disponible: ${credito_disponible:,.2f}, Total del pedido: ${total_pedido:,.2f}."
            )

        cursor.execute("""
            INSERT INTO pedidos (cliente_id, estado, total, observaciones_agente)
            VALUES (?, 'RECIBIDO', ?, ?)
        """, (pedido.cliente_id, total_pedido, pedido.observaciones_agente))
        pedido_id = cursor.lastrowid

        for det in detalles_a_procesar:
            cursor.execute("""
                INSERT INTO detalle_pedidos (pedido_id, producto_id, cantidad, precio_unitario)
                VALUES (?, ?, ?, ?)
            """, (pedido_id, det["producto_id"], det["cantidad"], det["precio_unitario"]))
            
            cursor.execute("""
                UPDATE productos 
                SET stock_fisico = stock_fisico - ? 
                WHERE id = ?
            """, (det["cantidad"], det["producto_id"]))

        nuevo_saldo = cliente["saldo_actual"] + total_pedido
        cursor.execute("""
            UPDATE clientes 
            SET saldo_actual = ? 
            WHERE id = ?
        """, (nuevo_saldo, pedido.cliente_id))

        cursor.execute("""
            INSERT INTO movimientos_cuenta (cliente_id, tipo, monto, pedido_id)
            VALUES (?, 'PEDIDO', ?, ?)
        """, (pedido.cliente_id, total_pedido, pedido_id))

        conexion.commit()
        return {
            "mensaje": "Pedido creado con éxito y validado por la API",
            "pedido_id": pedido_id,
            "total_pedido": total_pedido,
            "nuevo_saldo_cliente": nuevo_saldo
        }

    except HTTPException as he:
        conexion.rollback()
        raise he
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno al procesar el pedido: {str(e)}")
    finally:
        conexion.close()