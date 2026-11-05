from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sqlite3
from pathlib import Path
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import hashlib
from datetime import datetime
import re

# Importaciones para ReportLab (Generación de PDF)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = FastAPI(
    title="API Distribuidora de Limpieza",
    version="1.13",
    description="API B2B con Gestión de Clientes, Control de Stock, Categorías y Órdenes en PDF."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración de archivos estáticos para servir los PDFs generados
CARPETA_PDFS = Path(__file__).parent.parent / "documentos_pedidos"
CARPETA_PDFS.mkdir(parents=True, exist_ok=True)
app.mount("/documentos_pedidos", StaticFiles(directory=str(CARPETA_PDFS)), name="documentos_pedidos")

RUTA_DB = Path(__file__).parent.parent / "base_datos" / "distribuidora.db"

def obtener_conexion():
    if not RUTA_DB.exists():
        raise HTTPException(status_code=500, detail="La base de datos no existe. Ejecute crear_base_2.py primero.")
    conexion = sqlite3.connect(RUTA_DB)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion

def asegurar_columnas_clientes(cursor):
    """Verifica y agrega columnas faltantes en la tabla clientes de forma dinámica"""
    cursor.execute("PRAGMA table_info(clientes)")
    columnas = [col["name"] for col in cursor.fetchall()]
    
    if "telefono" not in columnas:
        cursor.execute("ALTER TABLE clientes ADD COLUMN telefono TEXT DEFAULT ''")
    if "condicion_fiscal" not in columnas:
        cursor.execute("ALTER TABLE clientes ADD COLUMN condicion_fiscal TEXT DEFAULT 'Responsable Inscripto'")
    if "medio_pago" not in columnas:
        cursor.execute("ALTER TABLE clientes ADD COLUMN medio_pago TEXT DEFAULT 'Efectivo contra entrega'")

def generar_hash(clave: str) -> str:
    return hashlib.sha256(clave.encode('utf-8')).hexdigest()

def validar_dni_cuil(valor: str) -> bool:
    limpio = re.sub(r'\D', '', valor)
    return 7 <= len(limpio) <= 11

def validar_clave_segura(clave: str) -> bool:
    if len(clave) < 8:
        return False
    if not re.search(r'[A-Za-z]', clave):
        return False
    if not re.search(r'\d', clave):
        return False
    return True


# ==========================================
# MODELOS PYDANTIC
# ==========================================

class UsuarioRegistro(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    dni_cuil: str
    clave: str
    confirmar_clave: str

class UsuarioLogin(BaseModel):
    email: EmailStr
    clave: str

class RecuperarPasswordModel(BaseModel):
    email: EmailStr

class ResetPasswordModel(BaseModel):
    email: EmailStr
    token: str
    nueva_clave: str
    confirmar_nueva_clave: str

class CambiarPasswordModel(BaseModel):
    usuario_id: int
    clave_actual: str
    nueva_clave: str
    confirmar_nueva_clave: str

class ClienteModel(BaseModel):
    razon_social: str
    cuit: str
    direccion: str
    condicion_fiscal: Optional[str] = "Responsable Inscripto"
    medio_pago: Optional[str] = "Efectivo contra entrega"
    telefono: Optional[str] = ""

class DetalleItem(BaseModel):
    producto_id: int
    cantidad: int

class PedidoCreate(BaseModel):
    cliente_id: Optional[int] = None
    datos_cliente: Optional[ClienteModel] = None
    observaciones_agente: Optional[str] = None
    items: List[DetalleItem]


# ==========================================
# ENDPOINTS DE AUTENTICACIÓN
# ==========================================

@app.post("/registro", summary="Registrar nuevo usuario con validaciones estrictas")
def registrar_usuario(datos: UsuarioRegistro):
    if not validar_dni_cuil(datos.dni_cuil):
        raise HTTPException(status_code=400, detail="El DNI o CUIT/CUIL ingresado no tiene un formato válido.")
    
    if datos.clave != datos.confirmar_clave:
        raise HTTPException(status_code=400, detail="Las contraseñas no coinciden.")
    
    if not validar_clave_segura(datos.clave):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres, incluyendo letras y números.")

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    try:
        cursor.execute("SELECT id FROM usuarios WHERE email = ? OR dni_cuil = ?", (datos.email, datos.dni_cuil))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="El email o DNI/CUIL ya se encuentran registrados en el sistema.")
        
        clave_hash = generar_hash(datos.clave)
        token_activacion = hashlib.md5(f"{datos.email}{datetime.now()}".encode('utf-8')).hexdigest()[:8].upper()
        
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellido, email, dni_cuil, clave_hash, rol, verificado, token_verificacion)
            VALUES (?, ?, ?, ?, ?, 'cliente', 0, ?)
        """, (datos.nombre, datos.apellido, datos.email, datos.dni_cuil, clave_hash, token_activacion))
        
        conexion.commit()
        
        return {
            "mensaje": "¡Registro exitoso! Se ha enviado un correo de activación a su casilla.",
            "email": datos.email,
            "token_debug": token_activacion
        }
    except HTTPException as he:
        conexion.rollback()
        raise he
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        conexion.close()

@app.post("/activar", summary="Activar cuenta mediante token enviado por mail")
def activar_cuenta(email: EmailStr, token: str):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT id, verificado FROM usuarios WHERE email = ? AND token_verificacion = ?", (email, token))
    usuario_row = cursor.fetchone()
    
    if not usuario_row:
        conexion.close()
        raise HTTPException(status_code=400, detail="Token de activación inválido o correo incorrecto.")
    
    usuario = dict(usuario_row)
    if usuario["verificado"] == 1:
        conexion.close()
        return {"mensaje": "La cuenta ya se encontraba activada."}
    
    cursor.execute("UPDATE usuarios SET verificado = 1, token_verificacion = NULL WHERE id = ?", (usuario["id"],))
    conexion.commit()
    conexion.close()
    
    return {"mensaje": "Cuenta activada con éxito. Ya puede iniciar sesión."}

@app.post("/login", summary="Iniciar sesión validando verificación")
def login_usuario(datos: UsuarioLogin):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    clave_hash = generar_hash(datos.clave)
    
    cursor.execute("""
        SELECT id, nombre, apellido, email, rol, verificado FROM usuarios 
        WHERE email = ? AND clave_hash = ?
    """, (datos.email, clave_hash))
    
    usuario_row = cursor.fetchone()
    conexion.close()
    
    if not usuario_row:
        raise HTTPException(status_code=401, detail="Credenciales incorrectas o usuario no encontrado.")
    
    usuario = dict(usuario_row)
    if usuario["verificado"] == 0:
        raise HTTPException(status_code=403, detail="Cuenta no activada. Por favor revise su correo electrónico para verificarla.")
    
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

@app.post("/recuperar-password", summary="Solicitar recuperación de contraseña")
def recuperar_password(datos: RecuperarPasswordModel):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT id FROM usuarios WHERE email = ?", (datos.email,))
    usuario = cursor.fetchone()
    
    if not usuario:
        conexion.close()
        raise HTTPException(status_code=404, detail="El correo electrónico no se encuentra registrado.")
    
    token_recuperacion = hashlib.md5(f"{datos.email}{datetime.now()}".encode('utf-8')).hexdigest()[:6].upper()
    
    cursor.execute("UPDATE usuarios SET token_verificacion = ? WHERE email = ?", (token_recuperacion, datos.email))
    conexion.commit()
    conexion.close()
    
    return {
        "mensaje": "Se ha enviado un correo con las instrucciones para restablecer su contraseña.",
        "token_debug": token_recuperacion
    }

@app.post("/resetear-password", summary="Restablecer nueva contraseña (doble verificación)")
def resetear_password(datos: ResetPasswordModel):
    if datos.nueva_clave != datos.confirmar_nueva_clave:
        raise HTTPException(status_code=400, detail="Las nuevas contraseñas no coinciden.")
    
    if not validar_clave_segura(datos.nueva_clave):
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 8 caracteres, letras y números.")

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    cursor.execute("SELECT id FROM usuarios WHERE email = ? AND token_verificacion = ?", (datos.email, datos.token))
    usuario = cursor.fetchone()
    
    if not usuario:
        conexion.close()
        raise HTTPException(status_code=400, detail="Código de recuperación inválido o expirado.")
    
    nuevo_hash = generar_hash(datos.nueva_clave)
    
    cursor.execute("UPDATE usuarios SET clave_hash = ?, token_verificacion = NULL WHERE email = ?", (nuevo_hash, datos.email))
    conexion.commit()
    conexion.close()
    
    return {"mensaje": "Contraseña actualizada con éxito. Ya puede iniciar sesión con su nueva clave."}

@app.post("/cambiar-password", summary="Cambiar contraseña de usuario autenticado")
def cambiar_password(datos: CambiarPasswordModel):
    if datos.nueva_clave != datos.confirmar_nueva_clave:
        raise HTTPException(status_code=400, detail="Las nuevas contraseñas no coinciden.")
    
    if not validar_clave_segura(datos.nueva_clave):
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 8 caracteres, letras y números.")

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    hash_actual = generar_hash(datos.clave_actual)
    cursor.execute("SELECT id FROM usuarios WHERE id = ? AND clave_hash = ?", (datos.usuario_id, hash_actual))
    usuario = cursor.fetchone()
    
    if not usuario:
        conexion.close()
        raise HTTPException(status_code=401, detail="La contraseña actual es incorrecta.")
    
    nuevo_hash = generar_hash(datos.nueva_clave)
    cursor.execute("UPDATE usuarios SET clave_hash = ? WHERE id = ?", (nuevo_hash, datos.usuario_id))
    conexion.commit()
    conexion.close()
    
    return {"mensaje": "Contraseña actualizada con éxito."}


# ==========================================
# MÓDULO DE PRODUCTOS, CATEGORÍAS, CLIENTES Y PEDIDOS
# ==========================================

@app.get("/productos", summary="Listar todos los productos activos con sus categorías")
def listar_productos():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM productos WHERE activo = 1")
    productos = [dict(fila) for fila in cursor.fetchall()]
    conexion.close()
    return productos

@app.get("/categorias", summary="Listar todas las categorías disponibles en el catálogo")
def listar_categorias():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT DISTINCT categoria FROM productos WHERE activo = 1 ORDER BY categoria ASC")
    categorias = [fila["categoria"] for fila in cursor.fetchall()]
    conexion.close()
    return categorias

@app.get("/clientes", summary="Listar clientes registrados")
def listar_clientes():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        asegurar_columnas_clientes(cursor)
        conexion.commit()

        cursor.execute("SELECT id, razon_social, cuit, direccion_entrega, telefono, condicion_fiscal, medio_pago, limite_credito, saldo_actual, estado FROM clientes ORDER BY id DESC")
        filas = cursor.fetchall()
        clientes = []
        for f in filas:
            cli = dict(f)
            cli["direccion"] = cli.get("direccion_entrega", "")
            cli["telefono"] = cli.get("telefono", "") or ""
            cli["condicion_fiscal"] = cli.get("condicion_fiscal", "") or "Responsable Inscripto"
            cli["medio_pago"] = cli.get("medio_pago", "") or "Efectivo contra entrega"
            clientes.append(cli)
        conexion.close()
        return clientes
    except Exception as e:
        conexion.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/clientes", summary="Crear nuevo cliente")
def crear_cliente(c: ClienteModel):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        asegurar_columnas_clientes(cursor)
        
        cursor.execute("""
            INSERT INTO clientes (razon_social, cuit, direccion_entrega, telefono, condicion_fiscal, medio_pago, limite_credito, saldo_actual, estado)
            VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, 'ACTIVO')
        """, (c.razon_social, c.cuit, c.direccion, c.telefono, c.condicion_fiscal, c.medio_pago))
        
        conexion.commit()
        cliente_id = cursor.lastrowid
        return {"mensaje": "Cliente creado con éxito", "id": cliente_id}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.put("/clientes/{cliente_id}", summary="Actualizar datos de cliente")
def actualizar_cliente(cliente_id: int, c: ClienteModel):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        asegurar_columnas_clientes(cursor)
        
        cursor.execute("""
            UPDATE clientes 
            SET razon_social = ?, cuit = ?, direccion_entrega = ?, telefono = ?, condicion_fiscal = ?, medio_pago = ?
            WHERE id = ?
        """, (c.razon_social, c.cuit, c.direccion, c.telefono, c.condicion_fiscal, c.medio_pago, cliente_id))
        
        conexion.commit()
        return {"mensaje": "Cliente actualizado con éxito"}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.delete("/clientes/{cliente_id}", summary="Eliminar cliente")
def eliminar_cliente(cliente_id: int):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
        conexion.commit()
        return {"mensaje": "Cliente eliminado con éxito"}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.post("/pedidos", summary="Crear pedido y generar PDF de la orden")
def crear_pedido(pedido: PedidoCreate):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        asegurar_columnas_clientes(cursor)

        if pedido.cliente_id:
            cursor.execute("SELECT * FROM clientes WHERE id = ?", (pedido.cliente_id,))
            cliente_row = cursor.fetchone()
            if not cliente_row:
                raise HTTPException(status_code=404, detail="El cliente especificado no existe.")
            cliente = dict(cliente_row)
            cliente_id = cliente["id"]
            cliente["direccion"] = cliente.get("direccion_entrega", "")
        elif pedido.datos_cliente:
            c = pedido.datos_cliente
            cursor.execute("""
                INSERT INTO clientes (razon_social, cuit, direccion_entrega, telefono, condicion_fiscal, medio_pago, limite_credito, saldo_actual, estado)
                VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, 'ACTIVO')
            """, (c.razon_social, c.cuit, c.direccion, c.telefono, c.condicion_fiscal, c.medio_pago))
                
            cliente_id = cursor.lastrowid
            cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
            cliente_row = cursor.fetchone()
            cliente = dict(cliente_row)
            cliente["direccion"] = cliente.get("direccion_entrega", "")
        else:
            raise HTTPException(status_code=400, detail="Debe seleccionar un cliente o completar sus datos.")

        total_pedido = 0.0
        detalles_a_procesar = []
        items_pdf_data = []

        for item in pedido.items:
            cursor.execute("SELECT * FROM productos WHERE id = ? AND activo = 1", (item.producto_id,))
            prod_row = cursor.fetchone()
            if not prod_row:
                raise HTTPException(status_code=404, detail=f"Producto ID {item.producto_id} no encontrado.")
            
            prod = dict(prod_row)
            if prod["stock_fisico"] < item.cantidad:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente para '{prod['nombre']}'.")
            
            subtotal = prod["precio"] * item.cantidad
            total_pedido += subtotal
            detalles_a_procesar.append({
                "producto_id": item.producto_id,
                "cantidad": item.cantidad,
                "precio_unitario": prod["precio"]
            })
            items_pdf_data.append([
                str(prod.get("codigo", "SKU")),
                str(prod["nombre"]),
                str(item.cantidad),
                f"${prod['precio']:,.2f}",
                f"${subtotal:,.2f}"
            ])

        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT INTO pedidos (cliente_id, fecha, estado, total, observaciones_agente)
            VALUES (?, ?, 'RECIBIDO', ?, ?)
        """, (cliente_id, fecha_actual, total_pedido, pedido.observaciones_agente))
        pedido_id = cursor.lastrowid

        for det in detalles_a_procesar:
            cursor.execute("""
                INSERT INTO detalle_pedidos (pedido_id, producto_id, cantidad, precio_unitario)
                VALUES (?, ?, ?, ?)
            """, (pedido_id, det["producto_id"], det["cantidad"], det["precio_unitario"]))
            cursor.execute("UPDATE productos SET stock_fisico = stock_fisico - ? WHERE id = ?", (det["cantidad"], det["producto_id"]))

        nuevo_saldo = cliente.get("saldo_actual", 0.0) + total_pedido
        cursor.execute("UPDATE clientes SET saldo_actual = ? WHERE id = ?", (nuevo_saldo, cliente_id))
        conexion.commit()

        # Generación del PDF con ReportLab (Diseño UI/UX Moderno)
        carpeta_docs = Path(__file__).parent.parent / "documentos_pedidos"
        carpeta_docs.mkdir(parents=True, exist_ok=True)
        nombre_archivo_pdf = f"orden_pedido_{pedido_id}.pdf"
        ruta_pdf = carpeta_docs / nombre_archivo_pdf

        doc = SimpleDocTemplate(str(ruta_pdf), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        elementos = []
        estilos = getSampleStyleSheet()

        color_primario = colors.HexColor('#1e40af')
        color_fondo_tarjeta = colors.HexColor('#f8fafc')
        color_borde = colors.HexColor('#e2e8f0')

        estilo_titulo = estilos['Heading1']
        estilo_titulo.textColor = color_primario
        estilo_titulo.fontSize = 20
        estilo_titulo.leading = 24

        elementos.append(Paragraph("<b>DistriApp Comercial</b>", estilo_titulo))
        elementos.append(Paragraph("<font color='#64748b' size=10>Portal B2B • Orden Oficial de Preventa y Logística</font>", estilos['Normal']))
        elementos.append(Spacer(1, 12))

        dir_cliente = cliente.get('direccion') or cliente.get('direccion_entrega') or 'N/D'
        cond_fiscal_cli = cliente.get('condicion_fiscal') or 'Responsable Inscripto'
        
        info_data = [
            [Paragraph(f"<b>Nº de Orden:</b> <font color='#1e40af'>#{pedido_id}</font>", estilos['Normal']), Paragraph(f"<b>Fecha de Emisión:</b> {fecha_actual}", estilos['Normal'])],
            [Paragraph(f"<b>Cliente / Razón Social:</b> {cliente.get('razon_social', 'N/D')}", estilos['Normal']), Paragraph(f"<b>CUIT / Identificación:</b> {cliente.get('cuit', 'N/D')}", estilos['Normal'])],
            [Paragraph(f"<b>Dirección de Destino:</b> {dir_cliente}", estilos['Normal']), Paragraph(f"<b>Condición Fiscal:</b> {cond_fiscal_cli}", estilos['Normal'])]
        ]
        t_info = Table(info_data, colWidths=[270, 270])
        t_info.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), color_fondo_tarjeta),
            ('PADDING', (0,0), (-1,-1), 10),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOX', (0,0), (-1,-1), 1, color_borde),
            ('INNERGRID', (0,0), (-1,-1), 0.5, color_borde),
        ]))
        elementos.append(t_info)
        elementos.append(Spacer(1, 15))

        tabla_items = [["SKU / Código", "Descripción del Producto", "Cant.", "Precio Unit.", "Subtotal"]] + items_pdf_data
        t_items = Table(tabla_items, colWidths=[80, 240, 50, 85, 85])
        t_items.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), color_primario),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (1,1), (1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 8),
            ('TOPPADDING', (0,0), (-1,0), 8),
            ('BACKGROUND', (0,1), (-1,-1), colors.white),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, color_fondo_tarjeta]),
            ('GRID', (0,0), (-1,-1), 0.5, color_borde),
            ('PADDING', (0,0), (-1,-1), 7),
            ('FONTSIZE', (0,1), (-1,-1), 9.5),
        ]))
        elementos.append(t_items)
        elementos.append(Spacer(1, 12))

        totales_data = [["", Paragraph(f"<font size=12><b>Total General:</b></font> <font size=14 color='#1e40af'><b>${total_pedido:,.2f}</b></font>", estilos['Normal'])]]
        t_totales = Table(totales_data, colWidths=[300, 240])
        t_totales.setStyle(TableStyle([
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('BACKGROUND', (1,0), (1,0), colors.HexColor('#dbeafe')),
            ('PADDING', (1,0), (1,0), 8),
            ('BOX', (1,0), (1,0), 1, colors.HexColor('#93c5fd')),
        ]))
        elementos.append(t_totales)
        
        if pedido.observaciones_agente:
            elementos.append(Spacer(1, 10))
            obs_data = [[Paragraph(f"<b>Observaciones / Logística:</b> {pedido.observaciones_agente}", estilos['Normal'])]]
            t_obs = Table(obs_data, colWidths=[540])
            t_obs.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), color_fondo_tarjeta),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BOX', (0,0), (-1,-1), 0.5, color_borde),
            ]))
            elementos.append(t_obs)

        doc.build(elementos)

        return {
            "mensaje": f"¡Pedido #{pedido_id} creado con éxito y PDF generado!",
            "pedido_id": pedido_id,
            "total_pedido": total_pedido,
            "pdf_generado": nombre_archivo_pdf
        }
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.get("/pedidos/todos", summary="Listar todos los pedidos registrados")
def listar_todos_pedidos():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT p.id, p.fecha, p.estado, p.total, p.observaciones_agente, c.razon_social 
        FROM pedidos p 
        LEFT JOIN clientes c ON p.cliente_id = c.id 
        ORDER BY p.fecha DESC
    """)
    pedidos = [dict(fila) for fila in cursor.fetchall()]
    conexion.close()
    return pedidos