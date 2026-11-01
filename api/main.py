from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
import hashlib
from datetime import datetime

app = FastAPI(
    title="API Distribuidora de Limpieza",
    version="1.0",
    description="API de la plataforma piloto para gestión de pedidos, stock, clientes y autenticación."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUTA_DB = Path(__file__).parent.parent / "base_datos" / "distribuidora.db"

def obtener_conexion():
    if not RUTA_DB.exists():
        raise HTTPException(status_code=500, detail="La base de datos no existe. Ejecute crear_base.py primero.")
    conexion = sqlite3.connect(RUTA_DB)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion

def generar_hash(clave: str) -> str:
    """Función para hashear la contraseña con SHA-256 de forma segura"""
    return hashlib.sha256(clave.encode('utf-8')).hexdigest()

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
# MÓDULO DE AUTENTICACIÓN Y USUARIOS
# ==========================================

class UsuarioRegistro(BaseModel):
    nombre: str
    apellido: str
    usuario: str
    email: str
    dni_cuil: str
    clave: str

class UsuarioLogin(BaseModel):
    email: str
    clave: str

@app.post("/registro", summary="Registrar nuevo usuario")
def registrar_usuario(datos: UsuarioRegistro):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        cursor.execute("SELECT id FROM usuarios WHERE email = ? OR dni_cuil = ?", (datos.email, datos.dni_cuil))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="El email o DNI/CUIL ya se encuentran registrados.")
        
        clave_hash = generar_hash(datos.clave)
        
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellido, usuario, email, dni_cuil, clave_hash, rol, verificado)
            VALUES (?, ?, ?, ?, ?, ?, 'cliente', 1)
        """, (datos.nombre, datos.apellido, datos.usuario, datos.email, datos.dni_cuil, clave_hash))
        
        conexion.commit()
        usuario_id = cursor.lastrowid
        return {
            "mensaje": "Usuario registrado con éxito.",
            "usuario_id": usuario_id,
            "email": datos.email
        }
    except sqlite3.IntegrityError as e:
        conexion.rollback()
        raise HTTPException(status_code=400, detail=f"Error de integridad en los datos: {str(e)}")
    except HTTPException as he:
        conexion.rollback()
        raise he
    finally:
        conexion.close()

@app.post("/login", summary="Iniciar sesión de usuario")
def login_usuario(datos: UsuarioLogin):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    clave_hash = generar_hash(datos.clave)
    
    cursor.execute("""
        SELECT id, nombre, apellido, email, rol FROM usuarios 
        WHERE email = ? AND clave_hash = ?
    """, (datos.email, clave_hash))
    
    usuario = cursor.fetchone()
    conexion.close()
    
    if not usuario:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas o usuario no encontrado.")
    
    return {
        "mensaje": "Login exitoso",
        "usuario": {
            "id": usuario["id"],
            "nombre": usuario["nombre"],
            "apellido": usuario["apellido"],
            "email": usuario["email"],
            "rol": usuario["rol"]
        }
    }


# ==========================================
# MÓDULO DE PEDIDOS (TRANSACCIONAL)
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

        # ==========================================
        # GENERACIÓN AUTOMÁTICA DE NOTA DE PEDIDO
        # ==========================================
        carpeta_docs = Path(__file__).parent.parent / "documentos_pedidos"
        carpeta_docs.mkdir(parents=True, exist_ok=True)
        
        nombre_archivo = carpeta_docs / f"pedido_{pedido_id}.txt"
        
        contenido_nota = f"""========================================
NOTA DE PEDIDO B2B - DISTRIBUIDORA
========================================
Nº de Pedido: #{pedido_id}
Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Cliente: {cliente['nombre']} {cliente['apellido']} (ID: {cliente['id']})
Email: {cliente['email']}
Estado: RECIBIDO
Observaciones: {pedido.observaciones_agente or 'Ninguna'}
----------------------------------------
DETALLE DE PRODUCTOS:
"""
        for det in detalles_a_procesar:
            cursor.execute("SELECT nombre FROM productos WHERE id = ?", (det["producto_id"],))
            prod_info = cursor.fetchone()
            nombre_prod = prod_info["nombre"] if prod_info else f"ID {det['producto_id']}"
            subtotal_item = det["cantidad"] * det["precio_unitario"]
            contenido_nota += f"- {nombre_prod} x {det['cantidad']} un. | Unitario: ${det['precio_unitario']:,.2f} | Subtotal: ${subtotal_item:,.2f}\n"

        contenido_nota += f"""----------------------------------------
TOTAL GENERAL: ${total_pedido:,.2f}
========================================
"""
        nombre_archivo.write_text(contenido_nota, encoding="utf-8")

        return {
            "mensaje": "Pedido creado con éxito, stock descontado y nota generada.",
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

@app.get("/pedidos/cliente/{cliente_id}", summary="Listar pedidos de un cliente específico")
def listar_pedidos_cliente(cliente_id: int):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT id, fecha, estado, total, observaciones_agente 
        FROM pedidos 
        WHERE cliente_id = ? 
        ORDER BY id DESC
    """, (cliente_id,))
    pedidos = [dict(fila) for fila in cursor.fetchall()]
    conexion.close()
    return pedidos