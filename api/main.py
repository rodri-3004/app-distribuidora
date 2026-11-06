from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sqlite3
from pathlib import Path
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import hashlib
import hmac
import os
import secrets
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
import re
import pandas as pd
import io

# Importaciones para ReportLab (Generación de PDF)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = FastAPI(
    title="API Distribuidora de Limpieza",
    version="1.36",
    description="API B2B con Modelo Profesional de Stock y Seguridad JWT."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CARPETA_PDFS = Path(__file__).parent.parent / "documentos_pedidos"
CARPETA_PDFS.mkdir(parents=True, exist_ok=True)
app.mount("/documentos_pedidos", StaticFiles(directory=str(CARPETA_PDFS)), name="documentos_pedidos")

RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "base_datos" / "distribuidora.db"

def obtener_conexion():
    if not RUTA_DB.exists():
        raise HTTPException(status_code=500, detail="La base de datos no existe.")
    conexion = sqlite3.connect(RUTA_DB)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion

def asegurar_esquema(cursor):
    cursor.execute("PRAGMA table_info(clientes)")
    col_clientes = [col["name"] for col in cursor.fetchall()]
    if "telefono" not in col_clientes:
        cursor.execute("ALTER TABLE clientes ADD COLUMN telefono TEXT DEFAULT ''")
    if "condicion_fiscal" not in col_clientes:
        cursor.execute("ALTER TABLE clientes ADD COLUMN condicion_fiscal TEXT DEFAULT 'Responsable Inscripto'")
    if "medio_pago" not in col_clientes:
        cursor.execute("ALTER TABLE clientes ADD COLUMN medio_pago TEXT DEFAULT 'Efectivo contra entrega'")
    if "usuario_dueno" not in col_clientes:
        cursor.execute("ALTER TABLE clientes ADD COLUMN usuario_dueno TEXT DEFAULT 'admin'")

    cursor.execute("PRAGMA table_info(pedidos)")
    col_pedidos = [col["name"] for col in cursor.fetchall()]
    if "usuario_id" not in col_pedidos:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN usuario_id INTEGER DEFAULT 1")

    cursor.execute("PRAGMA table_info(productos)")
    col_productos = [col["name"] for col in cursor.fetchall()]
    if "stock_reservado" not in col_productos:
        cursor.execute("ALTER TABLE productos ADD COLUMN stock_reservado INTEGER DEFAULT 0")

def generar_hash(clave: str) -> str:
    return hashlib.sha256(clave.encode('utf-8')).hexdigest()

# ==========================================
# SEGURIDAD: CONTRASEÑAS (bcrypt) Y SESIÓN (token JWT)
# ==========================================
def cargar_clave_jwt() -> str:
    clave = os.environ.get("JWT_SECRET")
    if clave:
        return clave
    ruta = Path(__file__).parent / ".jwt_secret"
    if not ruta.exists():
        ruta.write_text(secrets.token_hex(32))
    return ruta.read_text().strip()

CLAVE_JWT = cargar_clave_jwt()
HORAS_SESION = 8

def hashear_clave(clave: str) -> str:
    return bcrypt.hashpw(clave.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")

def verificar_clave(clave: str, hash_guardado: str) -> bool:
    if hash_guardado.startswith("$2"):
        return bcrypt.checkpw(clave.encode("utf-8")[:72], hash_guardado.encode("utf-8"))
    return hmac.compare_digest(generar_hash(clave), hash_guardado)

def crear_token(usuario: dict) -> str:
    ahora = datetime.now(timezone.utc)
    carga = {"sub": str(usuario["id"]), "rol": usuario["rol"], "iat": ahora, "exp": ahora + timedelta(hours=HORAS_SESION)}
    return jwt.encode(carga, CLAVE_JWT, algorithm="HS256")

esquema_bearer = HTTPBearer(auto_error=False)

def usuario_actual(credenciales: Optional[HTTPAuthorizationCredentials] = Depends(esquema_bearer)) -> dict:
    if credenciales is None:
        raise HTTPException(status_code=401, detail="Falta el token de sesión. Iniciá sesión de nuevo.")
    try:
        carga = jwt.decode(credenciales.credentials, CLAVE_JWT, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="La sesión expiró. Iniciá sesión de nuevo.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token de sesión inválido.")
    conexion = obtener_conexion()
    fila = conexion.execute("SELECT id, nombre, apellido, email, usuario, rol FROM usuarios WHERE id = ?", (carga["sub"],)).fetchone()
    conexion.close()
    if not fila:
        raise HTTPException(status_code=401, detail="El usuario de la sesión ya no existe.")
    return dict(fila)

def validar_dni_cuil(valor: str) -> bool:
    limpio = re.sub(r'\D', '', valor)
    return 7 <= len(limpio) <= 11

def validar_clave_segura(clave: str) -> bool:
    if len(clave) < 8 or not re.search(r'[A-Za-z]', clave) or not re.search(r'\d', clave):
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
    usuario_dueno: Optional[str] = "admin"

class DetalleItem(BaseModel):
    producto_id: int
    cantidad: int

class PedidoCreate(BaseModel):
    cliente_id: Optional[int] = None
    datos_cliente: Optional[ClienteModel] = None
    observaciones_agente: Optional[str] = None
    usuario_id: Optional[int] = 1  # Se ignora en el backend, se toma del token
    items: List[DetalleItem]


# ==========================================
# ENDPOINTS DE AUTENTICACIÓN
# ==========================================

@app.post("/registro", summary="Registrar nuevo usuario")
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
            raise HTTPException(status_code=400, detail="El email o DNI/CUIL ya se encuentran registrados.")
        
        clave_hash = hashear_clave(datos.clave)
        token_activacion = hashlib.md5(f"{datos.email}{datetime.now()}".encode('utf-8')).hexdigest()[:8].upper()
        
        username = datos.email.split("@")[0]
        cursor.execute("""
            INSERT INTO usuarios (nombre, apellido, email, dni_cuil, clave_hash, rol, verificado, token_verificacion, usuario)
            VALUES (?, ?, ?, ?, ?, 'cliente', 0, ?, ?)
        """, (datos.nombre, datos.apellido, datos.email, datos.dni_cuil, clave_hash, token_activacion, username))
        conexion.commit()
        
        return {"mensaje": "¡Registro exitoso! Ya puede iniciar sesión.", "email": datos.email, "token_debug": token_activacion}
    except HTTPException as he:
        conexion.rollback()
        raise he
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        conexion.close()

@app.post("/activar", summary="Activar cuenta mediante token simulado")
def activar_cuenta(email: EmailStr, token: str):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, verificado FROM usuarios WHERE email = ?", (email,))
    usuario_row = cursor.fetchone()
    
    if not usuario_row:
        conexion.close()
        raise HTTPException(status_code=400, detail="Correo electrónico no encontrado.")
    
    usuario = dict(usuario_row)
    if usuario["verificado"] == 1:
        conexion.close()
        return {"mensaje": "La cuenta ya se encontraba activada."}
    
    cursor.execute("UPDATE usuarios SET verificado = 1, token_verificacion = NULL WHERE id = ?", (usuario["id"],))
    conexion.commit()
    conexion.close()
    return {"mensaje": "¡Cuenta activada con éxito! Ya puede iniciar sesión."}

@app.post("/login", summary="Iniciar sesión: devuelve la identidad y un token de sesión")
def login_usuario(datos: UsuarioLogin):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT id, nombre, apellido, email, rol, verificado, usuario, clave_hash FROM usuarios
        WHERE email = ?
    """, (datos.email,))
    usuario_row = cursor.fetchone()

    if not usuario_row or not usuario_row["clave_hash"] or not verificar_clave(datos.clave, usuario_row["clave_hash"]):
        conexion.close()
        raise HTTPException(status_code=401, detail="Credenciales incorrectas o usuario no encontrado.")

    usuario = dict(usuario_row)
    if usuario["verificado"] == 0:
        conexion.close()
        raise HTTPException(status_code=403, detail="Cuenta no activada.")

    if not usuario["clave_hash"].startswith("$2"):
        cursor.execute("UPDATE usuarios SET clave_hash = ? WHERE id = ?", (hashear_clave(datos.clave), usuario["id"]))
        conexion.commit()
    conexion.close()

    username_asignado = usuario.get("usuario") or usuario["email"].split("@")[0]

    return {
        "mensaje": "Login exitoso",
        "access_token": crear_token(usuario),
        "token_type": "bearer",
        "usuario": {
            "id": usuario["id"],
            "nombre": usuario["nombre"],
            "apellido": usuario["apellido"],
            "email": usuario["email"],
            "rol": usuario["rol"],
            "username": username_asignado
        }
    }

@app.get("/yo", summary="Devuelve el usuario de la sesión actual")
def quien_soy(usuario: dict = Depends(usuario_actual)):
    return usuario

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
    
    return {"mensaje": "Correo de recuperación enviado.", "token_debug": token_recuperacion}

@app.post("/resetear-password", summary="Restablecer nueva contraseña")
def resetear_password(datos: ResetPasswordModel):
    if datos.nueva_clave != datos.confirmar_nueva_clave:
        raise HTTPException(status_code=400, detail="Las nuevas contraseñas no coinciden.")
    if not validar_clave_segura(datos.nueva_clave):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres, letras y números.")

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT id FROM usuarios WHERE email = ? AND token_verificacion = ?", (datos.email, datos.token))
    usuario = cursor.fetchone()
    
    if not usuario:
        conexion.close()
        raise HTTPException(status_code=400, detail="Código de recuperación inválido o expirado.")
    
    nuevo_hash = hashear_clave(datos.nueva_clave)
    cursor.execute("UPDATE usuarios SET clave_hash = ?, token_verificacion = NULL WHERE email = ?", (nuevo_hash, datos.email))
    conexion.commit()
    conexion.close()
    return {"mensaje": "Contraseña actualizada con éxito."}

@app.post("/cambiar-password", summary="Cambiar contraseña")
def cambiar_password(datos: CambiarPasswordModel):
    if datos.nueva_clave != datos.confirmar_nueva_clave:
        raise HTTPException(status_code=400, detail="Las nuevas contraseñas no coinciden.")
    if not validar_clave_segura(datos.nueva_clave):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres, letras y números.")

    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, clave_hash FROM usuarios WHERE id = ?", (datos.usuario_id,))
    usuario = cursor.fetchone()

    if not usuario or not usuario["clave_hash"] or not verificar_clave(datos.clave_actual, usuario["clave_hash"]):
        conexion.close()
        raise HTTPException(status_code=401, detail="La contraseña actual es incorrecta.")
    
    nuevo_hash = hashear_clave(datos.nueva_clave)
    cursor.execute("UPDATE usuarios SET clave_hash = ? WHERE id = ?", (nuevo_hash, datos.usuario_id))
    conexion.commit()
    conexion.close()
    return {"mensaje": "Contraseña actualizada con éxito."}


# ==========================================
# PRODUCTOS, CATEGORÍAS & IMPORTACIÓN
# ==========================================

@app.get("/productos", summary="Listar catálogo global")
def listar_productos():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    asegurar_esquema(cursor)
    conexion.commit()
    cursor.execute("SELECT *, (stock_fisico - stock_reservado) as stock_disponible FROM productos WHERE activo = 1")
    productos = [dict(fila) for fila in cursor.fetchall()]
    conexion.close()
    return productos

@app.get("/categorias", summary="Listar categorías del catálogo global")
def listar_categorias():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT DISTINCT categoria FROM productos WHERE activo = 1 ORDER BY categoria ASC")
    categorias = [fila["categoria"] for fila in cursor.fetchall()]
    conexion.close()
    return categorias

@app.post("/productos/importar-excel", summary="Actualizar precios masivamente")
async def importar_productos_excel(file: UploadFile = File(...), usuario: dict = Depends(usuario_actual)):
    contents = await file.read()
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        df.columns = [c.strip().lower() for c in df.columns]
        
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        asegurar_esquema(cursor)
        
        actualizados = 0
        for _, row in df.iterrows():
            codigo = str(row.get('codigo') or row.get('sku') or '').strip()
            precio = row.get('precio')
            
            if codigo and pd.notna(precio):
                cursor.execute("UPDATE productos SET precio = ? WHERE codigo = ?", (float(precio), codigo))
                actualizados += 1
                
        conexion.commit()
        conexion.close()
        return {"mensaje": f"Se actualizaron los precios de {actualizados} productos correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar la planilla: {str(e)}")


# ==========================================
# CLIENTES (PROTEGIDOS POR TOKEN)
# ==========================================

@app.get("/clientes", summary="Listar clientes exclusivos de la sesión del usuario")
def listar_clientes(usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        asegurar_esquema(cursor)
        conexion.commit()

        username = usuario_sesion.get("usuario") or usuario_sesion["email"].split("@")[0]

        if usuario_sesion["rol"] == "admin":
            cursor.execute("SELECT * FROM clientes ORDER BY id DESC")
        else:
            cursor.execute("SELECT * FROM clientes WHERE usuario_dueno = ? ORDER BY id DESC", (username,))
            
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

@app.post("/clientes", summary="Crear nuevo cliente vinculado a la sesión activa")
def crear_cliente(c: ClienteModel, usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        asegurar_esquema(cursor)
        username = usuario_sesion.get("usuario") or usuario_sesion["email"].split("@")[0]

        cursor.execute("""
            INSERT INTO clientes (razon_social, cuit, direccion_entrega, telefono, condicion_fiscal, medio_pago, limite_credito, saldo_actual, estado, usuario_dueno)
            VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, 'ACTIVO', ?)
        """, (c.razon_social, c.cuit, c.direccion, c.telefono, c.condicion_fiscal, c.medio_pago, username))
        conexion.commit()
        return {"mensaje": "Cliente creado con éxito en su cartera", "id": cursor.lastrowid}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.post("/clientes/importar-excel", summary="Importar clientes masivamente")
async def importar_clientes_excel(file: UploadFile = File(...), usuario_sesion: dict = Depends(usuario_actual)):
    contents = await file.read()
    try:
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        df.columns = [c.strip().lower() for c in df.columns]
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        asegurar_esquema(cursor)
        
        username = usuario_sesion.get("usuario") or usuario_sesion["email"].split("@")[0]
        importados = 0
        
        for _, row in df.iterrows():
            razon_social = str(row.get('razon_social') or row.get('nombre') or '').strip()
            cuit = str(row.get('cuit') or row.get('dni') or '').strip()
            direccion = str(row.get('direccion') or row.get('direccion_entrega') or '').strip()
            telefono = str(row.get('telefono') or '').strip()
            condicion = str(row.get('condicion_fiscal') or 'Responsable Inscripto').strip()
            pago = str(row.get('medio_pago') or 'Efectivo contra entrega').strip()
            
            if razon_social and cuit:
                cursor.execute("""
                    INSERT INTO clientes (razon_social, cuit, direccion_entrega, telefono, condicion_fiscal, medio_pago, limite_credito, saldo_actual, estado, usuario_dueno)
                    VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, 'ACTIVO', ?)
                """, (razon_social, cuit, direccion, telefono, condicion, pago, username))
                importados += 1
                
        conexion.commit()
        conexion.close()
        return {"mensaje": f"Se importaron {importados} clientes correctamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al importar clientes: {str(e)}")

@app.put("/clientes/{cliente_id}", summary="Actualizar datos de cliente")
def actualizar_cliente(cliente_id: int, c: ClienteModel, usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        asegurar_esquema(cursor)
        # Mantenemos el dueño original para no romper la cartera
        cursor.execute("SELECT usuario_dueno FROM clientes WHERE id = ?", (cliente_id,))
        dueno_row = cursor.fetchone()
        dueno = dueno_row["usuario_dueno"] if dueno_row else c.usuario_dueno

        cursor.execute("""
            UPDATE clientes 
            SET razon_social = ?, cuit = ?, direccion_entrega = ?, telefono = ?, condicion_fiscal = ?, medio_pago = ?, usuario_dueno = ?
            WHERE id = ?
        """, (c.razon_social, c.cuit, c.direccion, c.telefono, c.condicion_fiscal, c.medio_pago, dueno, cliente_id))
        conexion.commit()
        return {"mensaje": "Cliente actualizado con éxito"}
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.delete("/clientes/{cliente_id}", summary="Eliminar cliente")
def eliminar_cliente(cliente_id: int, usuario_sesion: dict = Depends(usuario_actual)):
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


# ==========================================
# PEDIDOS (PROTEGIDOS POR TOKEN)
# ==========================================

@app.post("/pedidos", summary="Crear pedido incrementando stock reservado")
def crear_pedido(pedido: PedidoCreate, usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        asegurar_esquema(cursor)

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
            username = usuario_sesion.get("usuario") or usuario_sesion["email"].split("@")[0]
            cursor.execute("""
                INSERT INTO clientes (razon_social, cuit, direccion_entrega, telefono, condicion_fiscal, medio_pago, limite_credito, saldo_actual, estado, usuario_dueno)
                VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, 'ACTIVO', ?)
            """, (c.razon_social, c.cuit, c.direccion, c.telefono, c.condicion_fiscal, c.medio_pago, username))
                
            cliente_id = cursor.lastrowid
            cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
            cliente = dict(cursor.fetchone())
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
            disponible = prod["stock_fisico"] - prod["stock_reservado"]
            if disponible < item.cantidad:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente para '{prod['nombre']}' (Disponible real: {disponible}).")
            
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
        
        # Usamos el ID del token, NO el del frontend
        cursor.execute("""
            INSERT INTO pedidos (cliente_id, fecha, estado, total, observaciones_agente, usuario_id)
            VALUES (?, ?, 'RECIBIDO', ?, ?, ?)
        """, (cliente_id, fecha_actual, total_pedido, pedido.observaciones_agente, usuario_sesion["id"]))
        pedido_id = cursor.lastrowid

        for det in detalles_a_procesar:
            cursor.execute("""
                INSERT INTO detalle_pedidos (pedido_id, producto_id, cantidad, precio_unitario)
                VALUES (?, ?, ?, ?)
            """, (pedido_id, det["producto_id"], det["cantidad"], det["precio_unitario"]))
            
            cursor.execute("""
                UPDATE productos
                SET stock_reservado = stock_reservado + ?
                WHERE id = ? AND (stock_fisico - stock_reservado) >= ?
            """, (det["cantidad"], det["producto_id"], det["cantidad"]))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=400, detail="El stock se agotó mientras se procesaba el pedido. Intente de nuevo.")

        nuevo_saldo = cliente.get("saldo_actual", 0.0) + total_pedido
        cursor.execute("UPDATE clientes SET saldo_actual = ? WHERE id = ?", (nuevo_saldo, cliente_id))
        conexion.commit()

        # Generación del PDF oficial con ReportLab
        nombre_archivo_pdf = f"orden_pedido_{pedido_id}.pdf"
        ruta_pdf = CARPETA_PDFS / nombre_archivo_pdf

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
            "mensaje": f"¡Pedido #{pedido_id} creado con éxito y reservado en depósito!",
            "pedido_id": pedido_id,
            "total_pedido": total_pedido,
            "pdf_generado": nombre_archivo_pdf
        }
    except HTTPException as he:
        conexion.rollback()
        raise he
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.post("/pedidos/{pedido_id}/preparar", summary="Preparar pedido: descuenta físico y reserva")
def preparar_pedido(pedido_id: int, usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,))
        pedido = cursor.fetchone()
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        
        if pedido["estado"] not in ("RECIBIDO", "VALIDADO"):
            raise HTTPException(status_code=400, detail=f"Solo se puede preparar un pedido RECIBIDO o VALIDADO (estado actual: {pedido['estado']}).")

        cursor.execute("SELECT producto_id, cantidad FROM detalle_pedidos WHERE pedido_id = ?", (pedido_id,))
        for det in cursor.fetchall():
            cursor.execute("""
                UPDATE productos
                SET stock_fisico = stock_fisico - ?, stock_reservado = stock_reservado - ?
                WHERE id = ? AND stock_reservado >= ? AND stock_fisico >= ?
            """, (det["cantidad"], det["cantidad"], det["producto_id"], det["cantidad"], det["cantidad"]))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=409, detail="Inconsistencia de stock: la reserva no alcanza.")

        cursor.execute("UPDATE pedidos SET estado = 'PREPARADO' WHERE id = ?", (pedido_id,))
        conexion.commit()
        return {"mensaje": f"Pedido #{pedido_id} preparado. Stock físico descontado."}
    except HTTPException:
        conexion.rollback()
        raise
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.post("/pedidos/{pedido_id}/cancelar", summary="Cancelar pedido: libera la reserva")
def cancelar_pedido(pedido_id: int, usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,))
        pedido = cursor.fetchone()
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        if pedido["estado"] == "CANCELADO":
            raise HTTPException(status_code=400, detail="El pedido ya estaba cancelado.")
        
        if pedido["estado"] not in ("RECIBIDO", "VALIDADO"):
            raise HTTPException(status_code=400, detail=f"Solo se puede cancelar un pedido RECIBIDO o VALIDADO.")

        cursor.execute("SELECT producto_id, cantidad FROM detalle_pedidos WHERE pedido_id = ?", (pedido_id,))
        for det in cursor.fetchall():
            cursor.execute("""
                UPDATE productos
                SET stock_reservado = stock_reservado - ?
                WHERE id = ? AND stock_reservado >= ?
            """, (det["cantidad"], det["producto_id"], det["cantidad"]))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=409, detail="Inconsistencia de stock: no hay reserva suficiente.")

        cursor.execute("UPDATE clientes SET saldo_actual = saldo_actual - ? WHERE id = ?", (pedido["total"], pedido["cliente_id"]))
        cursor.execute("UPDATE pedidos SET estado = 'CANCELADO' WHERE id = ?", (pedido_id,))
        conexion.commit()
        return {"mensaje": f"Pedido #{pedido_id} cancelado. Reserva liberada."}
    except HTTPException:
        conexion.rollback()
        raise
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.get("/pedidos/todos", summary="Listar historial de pedidos de la sesión")
def listar_todos_pedidos(usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    asegurar_esquema(cursor)
    conexion.commit()

    if usuario_sesion["rol"] == "admin":
        cursor.execute("""
            SELECT p.id, p.fecha, p.estado, p.total, p.observaciones_agente, c.razon_social, p.usuario_id
            FROM pedidos p 
            LEFT JOIN clientes c ON p.cliente_id = c.id 
            ORDER BY p.fecha DESC
        """)
    else:
        cursor.execute("""
            SELECT p.id, p.fecha, p.estado, p.total, p.observaciones_agente, c.razon_social, p.usuario_id
            FROM pedidos p 
            LEFT JOIN clientes c ON p.cliente_id = c.id 
            WHERE p.usuario_id = ?
            ORDER BY p.fecha DESC
        """, (usuario_sesion["id"],))
        
    pedidos = [dict(fila) for fila in cursor.fetchall()]
    conexion.close()
    return pedidos