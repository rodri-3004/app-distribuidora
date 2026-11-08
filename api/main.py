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
from datetime import datetime, timedelta, timezone, date
import re
import pandas as pd
import io

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

app = FastAPI(
    title="API Distribuidora de Limpieza",
    version="1.51",
    description="API B2B con Modelo Profesional, Seguridad JWT, Trazabilidad, Logística y Auditoría."
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
    if "estado_anterior" not in col_pedidos:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN estado_anterior TEXT")
    if "fecha_entrega" not in col_pedidos:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN fecha_entrega TEXT")

    cursor.execute("PRAGMA table_info(productos)")
    col_productos = [col["name"] for col in cursor.fetchall()]
    if "stock_reservado" not in col_productos:
        cursor.execute("ALTER TABLE productos ADD COLUMN stock_reservado INTEGER DEFAULT 0")
    if "imagen_url" not in col_productos:
        cursor.execute("ALTER TABLE productos ADD COLUMN imagen_url TEXT DEFAULT 'default.png'")
    if "stock_minimo" not in col_productos:
        cursor.execute("ALTER TABLE productos ADD COLUMN stock_minimo INTEGER DEFAULT 50")

def generar_hash(clave: str) -> str:
    return hashlib.sha256(clave.encode('utf-8')).hexdigest()

ESTADOS_CLIENTE = {
    "RECIBIDO": "Pendiente",
    "VALIDADO": "En preparación",
    "PREPARADO": "En preparación",
    "FACTURADO": "En preparación",
    "ARMADO": "Preparado para despachar",
    "CARGADO": "Preparado para despachar",
    "EN_REPARTO": "Pedido en camino",
    "ENTREGADO": "Pedido entregado",
    "CERRADO": "Pedido entregado",
    "EXCEPCION": "En revisión",
    "CANCELADO": "Cancelado"
}

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
    usuario_id: Optional[int] = 1
    fecha_entrega: Optional[str] = None
    items: List[DetalleItem]

class CambioEstadoModel(BaseModel):
    nuevo_estado: str

class ArmadoModel(BaseModel):
    bultos: int
    resultado: str
    detalle_diferencias: Optional[str] = None

class PlanificacionRutaModel(BaseModel):
    camion_id: int
    pedidos_ids: List[int]
    orden_carga: List[int]
    orden_entrega: List[int]

class EntregaModel(BaseModel):
    receptor: str
    resultado: str
    incidencia: Optional[str] = None
    comprobante: Optional[str] = None

class ExcepcionModel(BaseModel):
    pedido_id: int
    tipo: str
    motivo: str

class EventoModel(BaseModel):
    agente: str
    accion: str
    pedido_id: Optional[int] = None
    entrada_json: Optional[str] = None
    salida_json: Optional[str] = None
    evidencia: Optional[str] = None

def verificar_alerta_stock(cursor, producto_id: int):
    cursor.execute("SELECT id, nombre, stock_fisico, stock_reservado, stock_minimo FROM productos WHERE id = ?", (producto_id,))
    prod = cursor.fetchone()
    if not prod:
        return
    stock_disponible = prod["stock_fisico"] - prod["stock_reservado"]
    umbral = prod["stock_minimo"] if prod["stock_minimo"] is not None else 50
    if stock_disponible <= umbral:
        cursor.execute("SELECT id FROM alertas_stock WHERE producto_id = ? AND estado = 'PENDIENTE'", (producto_id,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO alertas_stock (producto_id, stock_actual, estado) VALUES (?, ?, 'PENDIENTE')", (producto_id, stock_disponible))

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

@app.post("/activar", summary="Activar cuenta")
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

@app.post("/login", summary="Iniciar sesión")
def login_usuario(datos: UsuarioLogin):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, nombre, apellido, email, rol, verificado, usuario, clave_hash FROM usuarios WHERE email = ?", (datos.email,))
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

@app.get("/yo", summary="Devuelve el usuario actual")
def quien_soy(usuario: dict = Depends(usuario_actual)):
    return usuario

@app.post("/recuperar-password", summary="Solicitar recuperación")
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
    return {"mensaje": "Correo enviado.", "token_debug": token_recuperacion}

@app.post("/resetear-password", summary="Restablecer contraseña")
def resetear_password(datos: ResetPasswordModel):
    if datos.nueva_clave != datos.confirmar_nueva_clave:
        raise HTTPException(status_code=400, detail="Las nuevas contraseñas no coinciden.")
    if not validar_clave_segura(datos.nueva_clave):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres.")
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
def cambiar_password(datos: CambiarPasswordModel, usuario_sesion: dict = Depends(usuario_actual)):
    if datos.nueva_clave != datos.confirmar_nueva_clave:
        raise HTTPException(status_code=400, detail="Las nuevas contraseñas no coinciden.")
    if not validar_clave_segura(datos.nueva_clave):
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 8 caracteres.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT id, clave_hash FROM usuarios WHERE id = ?", (usuario_sesion["id"],))
    usuario = cursor.fetchone()
    if not usuario or not usuario["clave_hash"] or not verificar_clave(datos.clave_actual, usuario["clave_hash"]):
        conexion.close()
        raise HTTPException(status_code=401, detail="La contraseña actual es incorrecta.")
    nuevo_hash = hashear_clave(datos.nueva_clave)
    cursor.execute("UPDATE usuarios SET clave_hash = ? WHERE id = ?", (nuevo_hash, usuario_sesion["id"]))
    conexion.commit()
    conexion.close()
    return {"mensaje": "Contraseña actualizada con éxito."}

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

@app.get("/categorias", summary="Listar categorías")
def listar_categorias():
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT DISTINCT categoria FROM productos WHERE activo = 1 ORDER BY categoria ASC")
    categorias = [fila["categoria"] for fila in cursor.fetchall()]
    conexion.close()
    return categorias

@app.post("/productos/importar-excel", summary="Actualizar precios masivamente")
async def importar_productos_excel(file: UploadFile = File(...), usuario: dict = Depends(usuario_actual)):
    if usuario["rol"] not in ("admin", "agente"):
        raise HTTPException(status_code=403, detail="Acceso denegado. Solo administradores o agentes pueden importar precios.")
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

@app.get("/clientes", summary="Listar clientes exclusivos de la sesión")
def listar_clientes(usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        asegurar_esquema(cursor)
        conexion.commit()
        username = usuario_sesion.get("usuario") or usuario_sesion["email"].split("@")[0]
        if usuario_sesion["rol"] in ("admin", "agente"):
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

@app.post("/clientes", summary="Crear nuevo cliente")
def crear_cliente(c: ClienteModel, usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        asegurar_esquema(cursor)
        username = usuario_sesion.get("usuario") or usuario_sesion["email"].split("@")[0]
        cursor.execute("INSERT INTO clientes (razon_social, cuit, direccion_entrega, telefono, condicion_fiscal, medio_pago, limite_credito, saldo_actual, estado, usuario_dueno) VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, 'ACTIVO', ?)", (c.razon_social, c.cuit, c.direccion, c.telefono, c.condicion_fiscal, c.medio_pago, username))
        conexion.commit()
        return {"mensaje": "Cliente creado con éxito en su cartera", "id": cursor.lastrowid}
    except sqlite3.IntegrityError:
        conexion.rollback()
        raise HTTPException(status_code=400, detail=f"El CUIT/DNI '{c.cuit}' ya está registrado. Por favor, verificá el número.")
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
                cursor.execute("INSERT INTO clientes (razon_social, cuit, direccion_entrega, telefono, condicion_fiscal, medio_pago, limite_credito, saldo_actual, estado, usuario_dueno) VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, 'ACTIVO', ?)", (razon_social, cuit, direccion, telefono, condicion, pago, username))
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
        cursor.execute("SELECT usuario_dueno FROM clientes WHERE id = ?", (cliente_id,))
        dueno_row = cursor.fetchone()
        dueno = dueno_row["usuario_dueno"] if dueno_row else c.usuario_dueno
        cursor.execute("UPDATE clientes SET razon_social=?, cuit=?, direccion_entrega=?, telefono=?, condicion_fiscal=?, medio_pago=?, usuario_dueno=? WHERE id=?", (c.razon_social, c.cuit, c.direccion, c.telefono, c.condicion_fiscal, c.medio_pago, dueno, cliente_id))
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

@app.get("/pedidos/todos", summary="Historial de pedidos")
def listar_todos_pedidos(usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    asegurar_esquema(cursor)
    conexion.commit()
    if usuario_sesion["rol"] in ("admin", "agente"):
        cursor.execute("SELECT p.id, p.fecha, p.estado, p.total, p.observaciones_agente, p.fecha_entrega, c.razon_social, p.usuario_id FROM pedidos p LEFT JOIN clientes c ON p.cliente_id = c.id ORDER BY p.fecha DESC")
    else:
        cursor.execute("SELECT p.id, p.fecha, p.estado, p.total, p.observaciones_agente, p.fecha_entrega, c.razon_social, p.usuario_id FROM pedidos p LEFT JOIN clientes c ON p.cliente_id = c.id WHERE p.usuario_id = ? ORDER BY p.fecha DESC", (usuario_sesion["id"],))
    res = []
    for f in cursor.fetchall():
        p = dict(f)
        p["estado_cliente"] = ESTADOS_CLIENTE.get(p["estado"], p["estado"])
        res.append(p)
    conexion.close()
    return res

@app.get("/pedidos/entrega/{fecha}", summary="Listar pedidos que se entregan en una fecha")
def listar_pedidos_por_fecha_entrega(fecha: str, usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            SELECT p.id, p.fecha, p.estado, p.total, p.fecha_entrega, c.razon_social
            FROM pedidos p
            LEFT JOIN clientes c ON p.cliente_id = c.id
            WHERE p.fecha_entrega = ?
            ORDER BY p.id ASC
        """, (fecha,))
        pedidos = [dict(f) for f in cursor.fetchall()]
        conexion.close()
        return pedidos
    except Exception as e:
        conexion.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pedidos", summary="Listar pedidos filtrados por estado")
def listar_pedidos_por_estado(estado: Optional[str] = None, usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        if estado:
            cursor.execute("""
                SELECT p.id, p.fecha, p.estado, p.total, p.fecha_entrega, c.razon_social
                FROM pedidos p
                LEFT JOIN clientes c ON p.cliente_id = c.id
                WHERE p.estado = ?
                ORDER BY p.fecha DESC
            """, (estado.upper(),))
        else:
            cursor.execute("""
                SELECT p.id, p.fecha, p.estado, p.total, p.fecha_entrega, c.razon_social
                FROM pedidos p
                LEFT JOIN clientes c ON p.cliente_id = c.id
                ORDER BY p.fecha DESC
            """)
        pedidos = [dict(f) for f in cursor.fetchall()]
        conexion.close()
        return pedidos
    except Exception as e:
        conexion.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pedidos", summary="Crear pedido")
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
            cursor.execute("INSERT INTO clientes (razon_social, cuit, direccion_entrega, telefono, condicion_fiscal, medio_pago, limite_credito, saldo_actual, estado, usuario_dueno) VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, 'ACTIVO', ?)", (c.razon_social, c.cuit, c.direccion, c.telefono, c.condicion_fiscal, c.medio_pago, username))
            cliente_id = cursor.lastrowid
            cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
            cliente = dict(cursor.fetchone())
            cliente["direccion"] = cliente.get("direccion_entrega", "")
        else:
            raise HTTPException(status_code=400, detail="Debe seleccionar un cliente o completar sus datos.")

        total = 0.0
        detalles = []
        pdf_data = []
        for item in pedido.items:
            cursor.execute("SELECT * FROM productos WHERE id = ? AND activo = 1", (item.producto_id,))
            prod_row = cursor.fetchone()
            if not prod_row:
                raise HTTPException(status_code=404, detail=f"Producto ID {item.producto_id} no encontrado.")
            prod = dict(prod_row)
            disponible = prod["stock_fisico"] - prod["stock_reservado"]
            if disponible < item.cantidad:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente para '{prod['nombre']}'.")
            subtotal = prod["precio"] * item.cantidad
            total += subtotal
            detalles.append({"producto_id": item.producto_id, "cantidad": item.cantidad, "precio_unitario": prod["precio"]})
            pdf_data.append([prod["codigo"], prod["nombre"], str(item.cantidad), f"${prod['precio']:,.2f}", f"${subtotal:,.2f}"])

        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        fecha_entrega_final = pedido.fecha_entrega if pedido.fecha_entrega else (date.today() + timedelta(days=1)).isoformat()
        
        cursor.execute("INSERT INTO pedidos (cliente_id, fecha, estado, total, observaciones_agente, usuario_id, fecha_entrega) VALUES (?, ?, 'RECIBIDO', ?, ?, ?, ?)", (cliente_id, fecha_actual, total, pedido.observaciones_agente, usuario_sesion["id"], fecha_entrega_final))
        pedido_id = cursor.lastrowid
        
        cursor.execute("INSERT INTO pedido_historial_estados (pedido_id, estado_anterior, estado_nuevo, cambiado_por) VALUES (?, NULL, 'RECIBIDO', ?)", (pedido_id, usuario_sesion.get("usuario") or usuario_sesion["email"]))
        
        for d in detalles:
            cursor.execute("INSERT INTO detalle_pedidos (pedido_id, producto_id, cantidad, precio_unitario) VALUES (?, ?, ?, ?)", (pedido_id, d["producto_id"], d["cantidad"], d["precio_unitario"]))
            cursor.execute("UPDATE productos SET stock_reservado = stock_reservado + ? WHERE id = ? AND (stock_fisico - stock_reservado) >= ?", (d["cantidad"], d["producto_id"], d["cantidad"]))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=400, detail="Stock agotado.")
            verificar_alerta_stock(cursor, d["producto_id"])
        cursor.execute("UPDATE clientes SET saldo_actual = saldo_actual + ? WHERE id = ?", (total, cliente_id))
        conexion.commit()

        nombre_pdf = f"orden_pedido_{pedido_id}.pdf"
        ruta_pdf = CARPETA_PDFS / nombre_pdf
        doc = SimpleDocTemplate(str(ruta_pdf), pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        elementos = []
        estilos = getSampleStyleSheet()
        cp = colors.HexColor('#1e3a8a')
        ct = colors.HexColor('#334155')
        cf = colors.HexColor('#f8fafc')
        cb = colors.HexColor('#e2e8f0')
        t_st = estilos['Heading1']
        t_st.textColor = cp
        t_st.fontSize = 24
        t_st.leading = 28
        t_st.alignment = 0
        s_st = estilos['Normal']
        s_st.textColor = colors.HexColor('#64748b')
        s_st.fontSize = 10
        elementos.append(Paragraph("<b>DistriApp</b>", t_st))
        elementos.append(Paragraph("Portal B2B • Orden Oficial", s_st))
        elementos.append(Spacer(1, 20))
        info = [
            [Paragraph(f"<b>Nº ORDEN</b><br/>#{pedido_id}", estilos['Normal']), Paragraph(f"<b>FECHA</b><br/>{fecha_actual}", estilos['Normal'])],
            [Paragraph(f"<b>CLIENTE</b><br/>{cliente['razon_social']}", estilos['Normal']), Paragraph(f"<b>CUIT</b><br/>{cliente['cuit']}", estilos['Normal'])],
            [Paragraph(f"<b>DIRECCIÓN</b><br/>{cliente['direccion']}", estilos['Normal']), Paragraph(f"<b>COND. FISCAL</b><br/>{cliente.get('condicion_fiscal','RI')}", estilos['Normal'])]
        ]
        ti = Table(info, colWidths=[260, 260])
        ti.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,-1), cf), ('PADDING', (0,0), (-1,-1), 12), ('BOX', (0,0), (-1,-1), 1, cb), ('INNERGRID', (0,0), (-1,-1), 1, colors.white)]))
        elementos.append(ti)
        elementos.append(Spacer(1, 30))
        tdata = [["SKU", "Producto", "Cant.", "P. Unit.", "Subtotal"]] + pdf_data
        ti2 = Table(tdata, colWidths=[70, 240, 50, 80, 80])
        ti2.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), cp), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('ALIGN', (0,0), (-1,-1), 'CENTER'), ('ALIGN', (1,1), (1,-1), 'LEFT'), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('PADDING', (0,0), (-1,-1), 10), ('GRID', (0,0), (-1,-1), 0.5, cb), ('TEXTCOLOR', (0,1), (-1,-1), ct)]))
        elementos.append(ti2)
        elementos.append(Spacer(1, 20))
        tot = [["", Paragraph(f"<b>Total:</b> <font size=18 color='#1e3a8a'><b>${total:,.2f}</b></font>", estilos['Normal'])]]
        ttot = Table(tot, colWidths=[320, 200])
        ttot.setStyle(TableStyle([('ALIGN', (1,0), (1,0), 'RIGHT')]))
        elementos.append(ttot)
        if pedido.observaciones_agente:
            elementos.append(Spacer(1, 20))
            obs = [[Paragraph(f"<b>OBS:</b> {pedido.observaciones_agente}", estilos['Normal'])]]
            tobs = Table(obs, colWidths=[520], style=[('BACKGROUND', (0,0), (-1,-1), cf), ('PADDING', (0,0), (-1,-1), 12), ('BOX', (0,0), (-1,-1), 1, cb)])
            elementos.append(tobs)
        doc.build(elementos)
        return {"mensaje": f"Pedido #{pedido_id} creado con éxito.", "pedido_id": pedido_id, "total": total, "pdf": nombre_pdf}
    except HTTPException:
        conexion.rollback()
        raise
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.get("/pedidos/{pedido_id}", summary="Obtener detalle completo de un pedido")
def obtener_pedido(pedido_id: int, usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,))
        pedido_row = cursor.fetchone()
        if not pedido_row:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        pedido = dict(pedido_row)
        cursor.execute("SELECT id, razon_social, cuit, direccion_entrega, saldo_actual, limite_credito FROM clientes WHERE id = ?", (pedido["cliente_id"],))
        pedido["cliente"] = dict(cursor.fetchone())
        cursor.execute("""
            SELECT dp.producto_id, dp.cantidad, dp.precio_unitario, p.codigo, p.nombre
            FROM detalle_pedidos dp
            JOIN productos p ON dp.producto_id = p.id
            WHERE dp.pedido_id = ?
        """, (pedido_id,))
        pedido["items"] = [dict(f) for f in cursor.fetchall()]
        conexion.close()
        return pedido
    except Exception as e:
        conexion.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pedidos/{pedido_id}/factura", summary="Ver factura del pedido")
def ver_factura(pedido_id: int, usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT * FROM facturas WHERE pedido_id = ?", (pedido_id,))
    fila = cursor.fetchone()
    conexion.close()
    
    if not fila: # Corrección del bug de cursor.rowcount
        raise HTTPException(status_code=404, detail="Factura no encontrada para este pedido.")
    return dict(fila)

@app.get("/pedidos/{pedido_id}/entrega", summary="Ver entrega del pedido")
def ver_entrega(pedido_id: int, usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT e.* FROM entregas e
        JOIN rutas_paradas rp ON e.parada_id = rp.id
        WHERE rp.pedido_id = ?
    """, (pedido_id,))
    fila = cursor.fetchone()
    conexion.close()

    if not fila: # Corrección del bug de cursor.rowcount
        raise HTTPException(status_code=404, detail="Entrega no encontrada para este pedido.")
    return dict(fila)

@app.post("/pedidos/{pedido_id}/asignar-fecha", summary="Asignar o cambiar la fecha de entrega")
def asignar_fecha_entrega(pedido_id: int, fecha: str, usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,))
        pedido = cursor.fetchone()
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        cursor.execute("UPDATE pedidos SET fecha_entrega = ? WHERE id = ?", (fecha, pedido_id))
        quien = usuario_sesion.get("usuario") or usuario_sesion["email"]
        cursor.execute("""
            INSERT INTO pedido_historial_estados (pedido_id, estado_anterior, estado_nuevo, fecha, cambiado_por)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
        """, (pedido_id, pedido["estado"], pedido["estado"], f"{quien} (cambió fecha de entrega a {fecha})"))
        conexion.commit()
        conexion.close()
        return {"mensaje": f"Fecha de entrega del pedido {pedido_id} actualizada a {fecha}."}
    except Exception as e:
        conexion.rollback()
        conexion.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/pedidos/{pedido_id}/estado", summary="Cambiar estado de un pedido")
def cambiar_estado_pedido(pedido_id: int, datos: CambioEstadoModel, usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    TRANS = {
        "RECIBIDO": ["VALIDADO", "EXCEPCION", "CANCELADO"],
        "VALIDADO": ["PREPARADO", "EXCEPCION", "CANCELADO"],
        "PREPARADO": ["FACTURADO", "EXCEPCION"], # FACTURADO debe ir por /facturar
        "FACTURADO": ["ARMADO", "EXCEPCION"],     # ARMADO debe ir por /armar
        "ARMADO": ["CARGADO", "EXCEPCION"],
        "CARGADO": ["EN_REPARTO", "EXCEPCION"],
        "EN_REPARTO": ["ENTREGADO", "EXCEPCION"],
        "ENTREGADO": ["CERRADO"],
        "EXCEPCION": ["RECIBIDO", "VALIDADO", "PREPARADO", "FACTURADO", "ARMADO", "CARGADO", "EN_REPARTO", "CANCELADO"]
    }
    try:
        cursor.execute("SELECT estado FROM pedidos WHERE id = ?", (pedido_id,))
        fila = cursor.fetchone()
        if not fila:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        est_act = fila["estado"]
        nuevo = datos.nuevo_estado.upper()
        if nuevo not in ESTADOS_CLIENTE:
            raise HTTPException(status_code=400, detail=f"Estado '{nuevo}' inválido.")
        if nuevo not in TRANS.get(est_act, []):
            raise HTTPException(status_code=400, detail=f"Transición inválida: {est_act} -> {nuevo}")
        
        # Sensores de Regla de Estado
        if nuevo == "FACTURADO":
            raise HTTPException(status_code=400, detail="Para facturar, usá POST /pedidos/{id}/facturar.")
        if nuevo == "ARMADO":
            raise HTTPException(status_code=400, detail="Para armar, usá POST /pedidos/{id}/armar.")

        if nuevo == "PREPARADO":
            cursor.execute("SELECT COUNT(*) as count FROM pedido_historial_estados WHERE pedido_id = ? AND estado_nuevo = 'PREPARADO'", (pedido_id,))
            ya_preparado = cursor.fetchone()["count"] > 0
            if not ya_preparado:
                cursor.execute("SELECT producto_id, cantidad FROM detalle_pedidos WHERE pedido_id = ?", (pedido_id,))
                for d in cursor.fetchall():
                    cursor.execute("UPDATE productos SET stock_fisico = stock_fisico - ?, stock_reservado = stock_reservado - ? WHERE id = ? AND stock_reservado >= ? AND stock_fisico >= ?", (d["cantidad"], d["cantidad"], d["producto_id"], d["cantidad"], d["cantidad"]))
                    if cursor.rowcount == 0:
                        raise HTTPException(status_code=409, detail="Inconsistencia de stock.")
                    verificar_alerta_stock(cursor, d["producto_id"])
                    
        if nuevo == "CANCELADO":
            cursor.execute("SELECT producto_id, cantidad FROM detalle_pedidos WHERE pedido_id = ?", (pedido_id,))
            for d in cursor.fetchall():
                cursor.execute("UPDATE productos SET stock_reservado = stock_reservado - ? WHERE id = ? AND stock_reservado >= ?", (d["cantidad"], d["producto_id"], d["cantidad"]))
            cursor.execute("UPDATE clientes SET saldo_actual = saldo_actual - (SELECT total FROM pedidos WHERE id = ?) WHERE id = (SELECT cliente_id FROM pedidos WHERE id = ?)", (pedido_id, pedido_id))
            
        quien = usuario_sesion.get("usuario") or usuario_sesion["email"]
        cursor.execute("UPDATE pedidos SET estado_anterior = estado, estado = ? WHERE id = ?", (nuevo, pedido_id))
        cursor.execute("INSERT INTO pedido_historial_estados (pedido_id, estado_anterior, estado_nuevo, cambiado_por) VALUES (?, ?, ?, ?)", (pedido_id, est_act, nuevo, quien))
        conexion.commit()
        return {"mensaje": f"Estado: {ESTADOS_CLIENTE[nuevo]}", "nuevo_estado": nuevo}
    except HTTPException:
        conexion.rollback()
        raise
    except Exception as e:
        conexion.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conexion.close()

@app.get("/pedidos/{pedido_id}/seguimiento", summary="Línea de tiempo")
def seguimiento_pedido(pedido_id: int, usuario_sesion: dict = Depends(usuario_actual)):
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT estado_anterior, estado_nuevo, fecha, cambiado_por FROM pedido_historial_estados WHERE pedido_id = ? ORDER BY fecha ASC", (pedido_id,))
        hist = []
        for f in cursor.fetchall():
            h = dict(f)
            h["estado_cliente"] = ESTADOS_CLIENTE.get(h["estado_nuevo"], h["estado_nuevo"])
            hist.append(h)
        conexion.close()
        return hist
    except Exception as e:
        conexion.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/excepciones", summary="Registrar una excepción")
def crear_excepcion(datos: ExcepcionModel, usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT estado FROM pedidos WHERE id = ?", (datos.pedido_id,))
        pedido = cursor.fetchone()
        if not pedido:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        
        if pedido["estado"] in ("CERRADO", "CANCELADO"):
            raise HTTPException(status_code=400, detail="No se puede abrir una excepción sobre un pedido ya cerrado o cancelado.")
            
        # 1. Insertar la excepción y capturar SU ID correcto
        cursor.execute("INSERT INTO excepciones (pedido_id, tipo, motivo, estado) VALUES (?, ?, ?, 'ABIERTA')", (datos.pedido_id, datos.tipo, datos.motivo))
        excepcion_id = cursor.lastrowid
        
        # 2. Actualizar el pedido
        cursor.execute("UPDATE pedidos SET estado = 'EXCEPCION' WHERE id = ?", (datos.pedido_id,))
        
        # 3. Registrar en el historial
        cursor.execute("INSERT INTO pedido_historial_estados (pedido_id, estado_anterior, estado_nuevo, cambiado_por) VALUES (?, ?, 'EXCEPCION', ?)", (datos.pedido_id, pedido["estado"], usuario_sesion["email"]))
        
        conexion.commit()
        conexion.close()
        return {"mensaje": "Excepción registrada.", "excepcion_id": excepcion_id}
    except HTTPException as he:
        conexion.rollback()
        conexion.close()
        raise he
    except Exception as e:
        conexion.rollback()
        conexion.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/excepciones", summary="Listar excepciones abiertas")
def listar_excepciones(usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT e.id, e.pedido_id, e.tipo, e.motivo, e.fecha, p.estado FROM excepciones e JOIN pedidos p ON e.pedido_id = p.id WHERE e.estado = 'ABIERTA' ORDER BY e.fecha DESC")
    res = [dict(f) for f in cursor.fetchall()]
    conexion.close()
    return res

@app.patch("/excepciones/{excepcion_id}/resolver", summary="Resolver una excepción")
def resolver_excepcion(excepcion_id: int, usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT estado FROM excepciones WHERE id = ?", (excepcion_id,))
        exc = cursor.fetchone()
        if not exc:
            raise HTTPException(status_code=404, detail="Excepción no encontrada.")
        if exc["estado"] == "RESUELTA":
            raise HTTPException(status_code=400, detail="Esta excepción ya fue resuelta.")

        cursor.execute("UPDATE excepciones SET estado = 'RESUELTA', resuelta_por = ? WHERE id = ?", (usuario_sesion["email"], excepcion_id))
        conexion.commit()
        conexion.close()
        return {"mensaje": "Excepción resuelta."}
    except HTTPException as he:
        conexion.rollback()
        conexion.close()
        raise he
    except Exception as e:
        conexion.rollback()
        conexion.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pedidos/{pedido_id}/facturar", summary="Emitir factura")
def facturar_pedido(pedido_id: int, usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,))
        p = cursor.fetchone()
        if not p:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        if p["estado"] != "PREPARADO":
            raise HTTPException(status_code=400, detail="El pedido debe estar PREPARADO.")
        subtotal = p["total"]
        impuestos = subtotal * 0.21
        total = subtotal + impuestos
        cursor.execute("SELECT COUNT(*) as count FROM facturas")
        count = cursor.fetchone()["count"]
        numero = f"FAC-{count + 1:04d}"
        cursor.execute("INSERT INTO facturas (pedido_id, numero, subtotal, impuestos, total, estado) VALUES (?, ?, ?, ?, ?, 'EMITIDA')", (pedido_id, numero, subtotal, impuestos, total))
        factura_id = cursor.lastrowid
        cursor.execute("INSERT INTO movimientos_cuenta (cliente_id, tipo, monto, pedido_id) VALUES (?, 'PEDIDO', ?, ?)", (p["cliente_id"], subtotal, pedido_id))
        cursor.execute("UPDATE pedidos SET estado_anterior = estado, estado = 'FACTURADO' WHERE id = ?", (pedido_id,))
        cursor.execute("INSERT INTO pedido_historial_estados (pedido_id, estado_anterior, estado_nuevo, cambiado_por) VALUES (?, 'PREPARADO', 'FACTURADO', ?)", (pedido_id, usuario_sesion["email"]))
        conexion.commit()
        conexion.close()
        return {"mensaje": "Factura emitida.", "factura_id": factura_id, "numero": numero, "total": total}
    except HTTPException:
        conexion.rollback()
        conexion.close()
        raise
    except Exception as e:
        conexion.rollback()
        conexion.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pedidos/{pedido_id}/armar", summary="Registrar armado")
def armar_pedido(pedido_id: int, datos: ArmadoModel, usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente", "operario"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,))
        p = cursor.fetchone()
        if not p:
            raise HTTPException(status_code=404, detail="Pedido no encontrado.")
        if p["estado"] != "FACTURADO":
            raise HTTPException(status_code=400, detail="El pedido debe estar FACTURADO.")
        cursor.execute("SELECT id FROM facturas WHERE pedido_id = ?", (pedido_id,))
        fact = cursor.fetchone()
        fid = fact["id"] if fact else None
        cursor.execute("INSERT INTO armados (pedido_id, factura_id, bultos, resultado, detalle_diferencias) VALUES (?, ?, ?, ?, ?)", (pedido_id, fid, datos.bultos, datos.resultado, datos.detalle_diferencias))
        cursor.execute("UPDATE pedidos SET estado_anterior = estado, estado = 'ARMADO' WHERE id = ?", (pedido_id,))
        cursor.execute("INSERT INTO pedido_historial_estados (pedido_id, estado_anterior, estado_nuevo, cambiado_por) VALUES (?, 'FACTURADO', 'ARMADO', ?)", (pedido_id, usuario_sesion["email"]))
        conexion.commit()
        conexion.close()
        return {"mensaje": "Pedido armado."}
    except HTTPException:
        conexion.rollback()
        conexion.close()
        raise
    except Exception as e:
        conexion.rollback()
        conexion.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rutas/planificar", summary="Planificar ruta")
def planificar_ruta(datos: PlanificacionRutaModel, usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT * FROM camiones WHERE id = ?", (datos.camion_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Camión no encontrado.")
        fecha = datetime.now().strftime('%Y-%m-%d')
        for i, pid in enumerate(datos.orden_carga):
            cursor.execute("SELECT estado FROM pedidos WHERE id = ?", (pid,))
            p = cursor.fetchone()
            if not p or p["estado"] != "ARMADO":
                raise HTTPException(status_code=400, detail=f"Pedido {pid} no está ARMADO (Estado actual: {p['estado'] if p else 'No existe'}).")
            ord_ent = datos.orden_entrega[i] if i < len(datos.orden_entrega) else 0
            cursor.execute("INSERT INTO rutas_paradas (camion_id, fecha, pedido_id, orden_carga, orden_entrega) VALUES (?, ?, ?, ?, ?)", (datos.camion_id, fecha, pid, i + 1, ord_ent))
            cursor.execute("UPDATE pedidos SET estado_anterior = estado, estado = 'CARGADO' WHERE id = ?", (pid,))
            cursor.execute("INSERT INTO pedido_historial_estados (pedido_id, estado_anterior, estado_nuevo, cambiado_por) VALUES (?, 'ARMADO', 'CARGADO', ?)", (pid, usuario_sesion["email"]))
        conexion.commit()
        conexion.close()
        return {"mensaje": f"Ruta planificada: {len(datos.orden_carga)} pedidos."}
    except HTTPException:
        conexion.rollback()
        conexion.close()
        raise
    except Exception as e:
        conexion.rollback()
        conexion.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/entregas/{pedido_id}", summary="Registrar entrega")
def registrar_entrega(pedido_id: int, datos: EntregaModel, usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente", "chofer"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("SELECT estado FROM pedidos WHERE id = ?", (pedido_id,))
        p = cursor.fetchone()
        if not p or p["estado"] not in ("CARGADO", "EN_REPARTO"):
            raise HTTPException(status_code=400, detail="El pedido debe estar CARGADO o EN_REPARTO.")
        cursor.execute("SELECT id FROM rutas_paradas WHERE pedido_id = ?", (pedido_id,))
        par = cursor.fetchone()
        if not par:
            cursor.execute("INSERT INTO rutas_paradas (camion_id, fecha, pedido_id, orden_carga, orden_entrega) VALUES (1, ?, ?, 1, 1)", (datetime.now().strftime('%Y-%m-%d'), pedido_id))
            par_id = cursor.lastrowid
        else:
            par_id = par["id"]
        hora = datetime.now().strftime('%H:%M:%S')
        cursor.execute("INSERT INTO entregas (parada_id, hora, receptor, resultado, incidencia, comprobante) VALUES (?, ?, ?, ?, ?, ?)", (par_id, hora, datos.receptor, datos.resultado, datos.incidencia, datos.comprobante))
        nuevo = 'ENTREGADO' if datos.resultado == 'ENTREGADO' else 'EXCEPCION'
        
        # Sensor: si la entrega falla, guardamos la incidencia como una excepción formal
        if nuevo == 'EXCEPCION':
            motivo_exc = datos.incidencia if datos.incidencia else "Entrega fallida sin detalle"
            cursor.execute("INSERT INTO excepciones (pedido_id, tipo, motivo, estado) VALUES (?, 'ENTREGA', ?, 'ABIERTA')", (pedido_id, motivo_exc))

        cursor.execute("UPDATE pedidos SET estado_anterior = estado, estado = ? WHERE id = ?", (nuevo, pedido_id))
        cursor.execute("INSERT INTO pedido_historial_estados (pedido_id, estado_anterior, estado_nuevo, cambiado_por) VALUES (?, ?, ?, ?)", (pedido_id, p["estado"], nuevo, usuario_sesion["email"]))
        conexion.commit()
        conexion.close()
        return {"mensaje": "Entrega registrada.", "nuevo_estado": nuevo}
    except HTTPException:
        conexion.rollback()
        conexion.close()
        raise
    except Exception as e:
        conexion.rollback()
        conexion.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alertas-stock/pendientes", summary="Alertas de stock bajo")
def obtener_alertas_pendientes(usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("SELECT a.id as alerta_id, a.fecha_generacion, a.stock_actual, p.id as producto_id, p.codigo, p.nombre, p.stock_fisico, p.stock_reservado FROM alertas_stock a JOIN productos p ON a.producto_id = p.id WHERE a.estado = 'PENDIENTE' ORDER BY a.fecha_generacion DESC")
    res = [dict(f) for f in cursor.fetchall()]
    conexion.close()
    return res

@app.patch("/alertas-stock/{alerta_id}/resolver", summary="Resolver alerta")
def resolver_alerta(alerta_id: int, usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    cursor.execute("UPDATE alertas_stock SET estado = 'RESUELTA' WHERE id = ?", (alerta_id,))
    conexion.commit()
    conexion.close()
    return {"mensaje": "Alerta resuelta."}

@app.post("/eventos", summary="Registrar un evento")
def crear_evento(evento: EventoModel, usuario_sesion: dict = Depends(usuario_actual)):
    if usuario_sesion["rol"] not in ("admin", "agente"):
        raise HTTPException(status_code=403, detail="Acceso denegado.")
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    try:
        cursor.execute("""
            INSERT INTO eventos_log (agente, pedido_id, accion, entrada_json, salida_json, evidencia)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (evento.agente, evento.pedido_id, evento.accion, evento.entrada_json, evento.salida_json, evento.evidencia))
        conexion.commit()
        conexion.close()
        return {"mensaje": "Evento registrado.", "evento_id": cursor.lastrowid}
    except Exception as e:
        conexion.rollback()
        conexion.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pedidos/{pedido_id}/preparar")
def preparar_pedido(pedido_id: int, usuario_sesion: dict = Depends(usuario_actual)):
    return cambiar_estado_pedido(pedido_id, CambioEstadoModel(nuevo_estado="PREPARADO"), usuario_sesion)

@app.post("/pedidos/{pedido_id}/cancelar")
def cancelar_pedido(pedido_id: int, usuario_sesion: dict = Depends(usuario_actual)):
    return cambiar_estado_pedido(pedido_id, CambioEstadoModel(nuevo_estado="CANCELADO"), usuario_sesion)