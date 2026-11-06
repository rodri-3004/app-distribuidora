import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import random

# Importaciones para ReportLab (Generación de PDF)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# Rutas robustas
RUTA_DB = Path(__file__).parent / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent / "base_datos" / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "base_datos" / "distribuidora.db"

CARPETA_PDFS = RUTA_DB.parent.parent / "documentos_pedidos"
if not CARPETA_PDFS.exists():
    CARPETA_PDFS = Path(__file__).parent / "documentos_pedidos"
CARPETA_PDFS.mkdir(parents=True, exist_ok=True)

def poblar_datos_masivos():
    if not RUTA_DB.exists():
        print(f"❌ Error: No se encontró la base de datos en {RUTA_DB}")
        return

    conexion = sqlite3.connect(RUTA_DB)
    conexion.row_factory = sqlite3.Row
    cursor = conexion.cursor()

    print("🔄 Conectado a la base de datos. Iniciando proceso masivo...")

    # 1. REPOBLAR STOCK DE PRODUCTOS
    cursor.execute("""
        UPDATE productos 
        SET stock_fisico = 500, stock_reservado = 0 
        WHERE activo = 1
    """)
    print("✅ Stock de todos los productos actualizado a 500 unidades disponibles.")

    # 2. OBTENER USUARIOS OBJETIVO
    cursor.execute("SELECT id, usuario, email FROM usuarios")
    todos_usuarios = cursor.fetchall()
    
    mapeo_usuarios = []
    for u in todos_usuarios:
        uid = u['id']
        uname = u['usuario'] or ''
        email = u['email'] or ''
        if 'admin' in email.lower() or 'admin' in uname.lower():
            mapeo_usuarios.append({'id': uid, 'username': uname or 'admin'})
        elif 'roberbola' in email.lower() or 'rober' in uname.lower():
            mapeo_usuarios.append({'id': uid, 'username': uname or 'roberbola'})

    if len(mapeo_usuarios) < 2:
        cursor.execute("SELECT id, usuario FROM usuarios LIMIT 2")
        mapeo_usuarios = [{'id': row['id'], 'username': row['usuario'] or f"user_{row['id']}"} for row in cursor.fetchall()]

    if not mapeo_usuarios:
        print("❌ No se encontraron usuarios en la base de datos. Registra al menos un usuario primero.")
        conexion.close()
        return

    nombres_empresas = [
        "Kiosco El Rápido", "Autoservicio Don Juan", "Almacén La Esquina", "Minimercado Sol",
        "Supermercado San Cayetano", "Comestibles Baires", "Maxikiosco Central", "Despensa Los Amigos",
        "Bazar y Limpieza 24hs", "Distribuidora Sur", "Comercializadora Norte", "Negocio de Barrio",
        "Kiosco Estación", "Almacén Doña Rosa", "Autoservicio Express", "Maxi Ahorro",
        "Punto de Venta Total", "Mercado Económico", "Comercial San José", "Kiosco Boulevard"
    ]

    condiciones = ["Responsable Inscripto", "Monotributo", "Consumidor Final"]
    pagos = ["Efectivo contra entrega", "Transferencia Bancaria", "Cuenta Corriente 30 días"]

    # Estilos globales para la generación de PDFs
    estilos = getSampleStyleSheet()
    color_primario = colors.HexColor('#1e40af')
    color_fondo_tarjeta = colors.HexColor('#f8fafc')
    color_borde = colors.HexColor('#e2e8f0')

    # 3. GENERAR CLIENTES Y PEDIDOS
    for usr in mapeo_usuarios:
        uid = usr['id']
        uname = usr['username']
        print(f"\n--- Procesando usuario ID: {uid} ({uname}) ---")

        ids_clientes_detalles = []
        for i in range(20):
            razon = f"{random.choice(nombres_empresas)} {random.randint(100, 999)}"
            cuit = f"20-{random.randint(10000000, 99999999)}-{random.randint(0,9)}"
            dir_entrega = f"Av. Principal {random.randint(100, 5000)}"
            tel = f"11{random.randint(40000000, 99999999)}"
            cond = random.choice(condiciones)
            pago = random.choice(pagos)

            cursor.execute("""
                INSERT INTO clientes (razon_social, cuit, direccion_entrega, telefono, condicion_fiscal, medio_pago, limite_credito, saldo_actual, estado, usuario_dueno)
                VALUES (?, ?, ?, ?, ?, ?, 0.0, 0.0, 'ACTIVO', ?)
            """, (razon, cuit, dir_entrega, tel, cond, pago, uname))
            
            c_id = cursor.lastrowid
            ids_clientes_detalles.append({
                "id": c_id,
                "razon_social": razon,
                "cuit": cuit,
                "direccion": dir_entrega,
                "condicion_fiscal": cond
            })

        print(f"✅ Se crearon 20 clientes para {uname}.")

        cursor.execute("SELECT id, codigo, nombre, precio FROM productos WHERE activo = 1")
        productos = cursor.fetchall()

        for p in range(300):
            cli = random.choice(ids_clientes_detalles)
            dias_atras = random.randint(0, 90)
            fecha_pedido = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%d %H:%M:%S')
            
            num_items = random.randint(1, 5)
            items_pedido = random.sample(productos, min(num_items, len(productos)))

            total_pedido = 0.0
            detalles = []
            items_pdf_data = []

            for prod in items_pedido:
                cant = random.randint(1, 10)
                subtotal = prod['precio'] * cant
                total_pedido += subtotal
                detalles.append((prod['id'], cant, prod['precio']))
                items_pdf_data.append([
                    str(prod['codigo'] or 'SKU'),
                    str(prod['nombre']),
                    str(cant),
                    f"${prod['precio']:,.2f}",
                    f"${subtotal:,.2f}"
                ])

            # Insertar pedido
            cursor.execute("""
                INSERT INTO pedidos (cliente_id, fecha, estado, total, observaciones_agente, usuario_id)
                VALUES (?, ?, 'RECIBIDO', ?, 'Generado por carga masiva automática', ?)
            """, (cli['id'], fecha_pedido, total_pedido, uid))
            pedido_id = cursor.lastrowid

            for prod_id, cant, precio in detalles:
                cursor.execute("""
                    INSERT INTO detalle_pedidos (pedido_id, producto_id, cantidad, precio_unitario)
                    VALUES (?, ?, ?, ?)
                """, (pedido_id, prod_id, cant, precio))

            # Generar PDF físico inmediatamente
            nombre_archivo_pdf = f"orden_pedido_{pedido_id}.pdf"
            ruta_pdf = CARPETA_PDFS / nombre_archivo_pdf

            doc = SimpleDocTemplate(str(ruta_pdf), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
            elementos = []
            
            estilo_titulo = estilos['Heading1']
            estilo_titulo.textColor = color_primario
            estilo_titulo.fontSize = 20
            estilo_titulo.leading = 24

            elementos.append(Paragraph("<b>DistriApp Comercial</b>", estilo_titulo))
            elementos.append(Paragraph("<font color='#64748b' size=10>Portal B2B • Orden Oficial de Preventa y Logística</font>", estilos['Normal']))
            elementos.append(Spacer(1, 12))

            info_data = [
                [Paragraph(f"<b>Nº de Orden:</b> <font color='#1e40af'>#{pedido_id}</font>", estilos['Normal']), Paragraph(f"<b>Fecha de Emisión:</b> {fecha_pedido}", estilos['Normal'])],
                [Paragraph(f"<b>Cliente / Razón Social:</b> {cli['razon_social']}", estilos['Normal']), Paragraph(f"<b>CUIT / Identificación:</b> {cli['cuit']}", estilos['Normal'])],
                [Paragraph(f"<b>Dirección de Destino:</b> {cli['direccion']}", estilos['Normal']), Paragraph(f"<b>Condición Fiscal:</b> {cli['condicion_fiscal']}", estilos['Normal'])]
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
            doc.build(elementos)

        print(f"✅ Se generaron 300 pedidos y sus respectivos PDFs para {uname}.")

    conexion.commit()
    conexion.close()
    print("\n🎉 ¡Proceso masivo y generación de PDFs completados con éxito!")

if __name__ == "__main__":
    poblar_datos_masivos()