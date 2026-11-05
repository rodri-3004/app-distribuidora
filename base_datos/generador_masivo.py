import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import random

# Importaciones para ReportLab (Generación oficial de PDFs)
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# Rutas absolutas seguras basadas en la ubicación de este archivo
BASE_DIR = Path(__file__).parent.parent
RUTA_DB = BASE_DIR / "base_datos" / "distribuidora.db"
CARPETA_PDFS = BASE_DIR / "documentos_pedidos"
CARPETA_PDFS.mkdir(parents=True, exist_ok=True)

def conectar():
    if not RUTA_DB.exists():
        raise FileNotFoundError(f"No se encontró la base de datos en {RUTA_DB}")
    conexion = sqlite3.connect(RUTA_DB)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion

def generar_datos_masivos():
    print("🚀 Iniciando la generación de productos, pedidos y PDFs oficiales...")
    conexion = conectar()
    cursor = conexion.cursor()

    # Desactivar temporalmente claves foráneas para limpiar datos anteriores de forma segura
    cursor.execute("PRAGMA foreign_keys = OFF;")
    cursor.execute("DELETE FROM detalle_pedidos")
    cursor.execute("DELETE FROM pedidos")
    cursor.execute("DELETE FROM productos")

    # 1. CATÁLOGO COMPLETO DE PRODUCTOS DE LIMPIEZA
    productos_limpieza = [
        # Ropa y Lavado
        ("ROP-001", "Jabón Líquido para Ropa Ala 3L", "Ropa y Lavado", 4850.0, 120, 0, 3.2, 3.0),
        ("ROP-002", "Jabón en Polvo Skip Matic 3kg", "Ropa y Lavado", 6200.0, 90, 0, 3.0, 3.1),
        ("ROP-003", "Suavizante para Ropa Vivere 3L", "Ropa y Lavado", 3900.0, 110, 0, 3.1, 3.0),
        ("ROP-004", "Quitamanchas Ropa Zorro 500ml", "Ropa y Lavado", 2400.0, 80, 0, 0.5, 0.5),
        ("ROP-005", "Jabón Blanco en Pan Federal 200g", "Ropa y Lavado", 650.0, 350, 0, 0.2, 0.2),
        ("ROP-006", "Jabón Líquido Zorro Doypack 800ml", "Ropa y Lavado", 3100.0, 140, 0, 0.8, 0.8),
        ("ROP-007", "Suavizante Concentrado Comfort 500ml", "Ropa y Lavado", 2800.0, 75, 0, 0.5, 0.5),
        ("ROP-008", "Blanqueador sin Cloro Magistral Ropa 1L", "Ropa y Lavado", 2600.0, 95, 0, 1.0, 1.0),
        ("ROP-009", "Almidón para Ropa Planchado Fácil 500ml", "Ropa y Lavado", 1750.0, 60, 0, 0.5, 0.5),
        ("ROP-010", "Detergente para Ropa Fina Leodrin 1L", "Ropa y Lavado", 3400.0, 50, 0, 1.0, 1.0),

        # Superficies y Pisos
        ("PIS-001", "Desinfectante de Pisos Cif 1.8L", "Superficies y Pisos", 3100.0, 150, 0, 1.9, 1.8),
        ("PIS-002", "Limpiador Líquido Lysoform 450ml", "Superficies y Pisos", 2250.0, 100, 0, 0.5, 0.5),
        ("PIS-003", "Cera Líquida Autobrillo Marlo 1L", "Superficies y Pisos", 2950.0, 60, 0, 1.1, 1.0),
        ("PIS-004", "Lavandina Concentrada Ayudín 1L", "Superficies y Pisos", 1450.0, 200, 0, 1.1, 1.0),
        ("PIS-005", "Limpiador Desinfectante Lysoform Piso 1.25L", "Superficies y Pisos", 4100.0, 110, 0, 1.3, 1.25),
        ("PIS-006", "Cera en Pasta Roja Gleet 400g", "Superficies y Pisos", 2300.0, 45, 0, 0.4, 0.4),
        ("PIS-007", "Alcohol Etílico 96° Sanitizante 1L", "Superficies y Pisos", 1900.0, 250, 0, 0.9, 1.0),
        ("PIS-008", "Limpiador Multiuso en Gatillo Cif 500ml", "Superficies y Pisos", 2650.0, 180, 0, 0.6, 0.5),
        ("PIS-009", "Mata Cucarachas y Bichos Raid 360ml", "Superficies y Pisos", 3800.0, 85, 0, 0.4, 0.4),
        ("PIS-010", "Insecticida Aerosol Repelente Off 165ml", "Superficies y Pisos", 3500.0, 90, 0, 0.2, 0.2),

        # Baños y Sanitarios
        ("BAN-001", "Limpiador en Gel Pato Purific 500g", "Baños y Sanitarios", 2800.0, 130, 0, 0.6, 0.5),
        ("BAN-002", "Desincrustante y Harpic 500ml", "Baños y Sanitarios", 2600.0, 95, 0, 0.5, 0.5),
        ("BAN-003", "Pastilla Tanque Inodoro Harpic", "Baños y Sanitarios", 1200.0, 180, 0, 0.1, 0.1),
        ("BAN-004", "Ácido Muriático para Limpieza 1L", "Baños y Sanitarios", 1850.0, 70, 0, 1.1, 1.0),
        ("BAN-005", "Destap Cañerías Líquido Mr Musculo 500ml", "Baños y Sanitarios", 4200.0, 65, 0, 0.6, 0.5),
        ("BAN-006", "Pastilla Adhesiva Pato Power 36g", "Baños y Sanitarios", 1400.0, 140, 0, 0.1, 0.1),
        ("BAN-007", "Desodorante de Inodoro Colgante Bref", "Baños y Sanitarios", 1550.0, 125, 0, 0.15, 0.15),
        ("BAN-008", "Limpiador Antisarro Baño Cif 500ml", "Baños y Sanitarios", 2900.0, 105, 0, 0.6, 0.5),
        ("BAN-009", "Jabón Líquido Manos Dispenser 250ml", "Baños y Sanitarios", 2100.0, 160, 0, 0.3, 0.25),
        ("BAN-010", "Repuesto Jabón Líquido Manos Algabo 1L", "Baños y Sanitarios", 3600.0, 80, 0, 1.0, 1.0),

        # Cocina y Desengrasantes
        ("COC-001", "Detergente Magistral 500ml", "Cocina y Desengrasantes", 2335.0, 250, 0, 0.5, 0.5),
        ("COC-002", "Desengrasante Cif Gatillo 500ml", "Cocina y Desengrasantes", 3476.0, 140, 0, 0.6, 0.6),
        ("COC-003", "Limpia Hornos Cif Aerosol 360g", "Cocina y Desengrasantes", 2865.0, 75, 0, 0.4, 0.4),
        ("COC-004", "Detergente Zorro Limón 750ml", "Cocina y Desengrasantes", 1900.0, 190, 0, 0.8, 0.75),
        ("COC-005", "Brilla Metales en Pasta Silvo 75g", "Cocina y Desengrasantes", 2450.0, 50, 0, 0.1, 0.1),
        ("COC-006", "Lavandina en Gel Cif Cocina 750ml", "Cocina y Desengrasantes", 2700.0, 110, 0, 0.8, 0.75),
        ("COC-007", "Esponja de Acero Inoxidable (Pack x2)", "Cocina y Desengrasantes", 800.0, 220, 0, 0.1, 0.1),
        ("COC-008", "Limpiador de Acero Inoxidable Cif 250ml", "Cocina y Desengrasantes", 3150.0, 60, 0, 0.3, 0.25),
        ("COC-009", "Pastillas Lavavajillas Menor x10u", "Cocina y Desengrasantes", 4500.0, 70, 0, 0.3, 0.3),
        ("COC-010", "Abrillantador de Vajilla Finish 250ml", "Cocina y Desengrasantes", 3900.0, 55, 0, 0.3, 0.25),

        # Accesorios y Utensilios
        ("ACC-001", "Esponja Multiuso Vileda (Pack x3)", "Accesorios y Utensilios", 950.0, 300, 0, 0.1, 0.2),
        ("ACC-002", "Guantes de Látex Reforzados (Talle M)", "Accesorios y Utensilios", 1600.0, 160, 0, 0.2, 0.1),
        ("ACC-003", "Papel Higiénico Higienol Doble Hoja 4u", "Accesorios y Utensilios", 1950.0, 220, 0, 0.5, 1.2),
        ("ACC-004", "Rollo de Cocina Elite Clásico 3u", "Accesorios y Utensilios", 2100.0, 180, 0, 0.4, 0.9),
        ("ACC-005", "Mopa de Microfibra con Cabo", "Accesorios y Utensilios", 7500.0, 45, 0, 1.2, 2.5),
        ("ACC-006", "Secador de Piso Metálico 40cm", "Accesorios y Utensilios", 3200.0, 90, 0, 0.8, 1.5),
        ("ACC-007", "Basurero con Pedal Plástico 15L", "Accesorios y Utensilios", 9800.0, 35, 0, 1.5, 4.0),
        ("ACC-008", "Paño de Microfibra Multiuso (Pack x3)", "Accesorios y Utensilios", 1850.0, 210, 0, 0.2, 0.3),
        ("ACC-009", "Escobillón de Cerdas Suaves con Cabo", "Accesorios y Utensilios", 4100.0, 80, 0, 1.0, 2.0),
        ("ACC-010", "Guantes de Goma para Limpieza Industrial", "Accesorios y Utensilios", 2300.0, 110, 0, 0.3, 0.2)
    ]

    cursor.executemany("""
        INSERT INTO productos (codigo, nombre, categoria, precio, stock_fisico, stock_reservado, peso_kg, volumen_dm3, imagen_url, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'default.png', 1)
    """, productos_limpieza)

    cursor.execute("PRAGMA foreign_keys = ON;")

    # 2. RECUPERAR CLIENTES Y PRODUCTOS INSERTADOS
    cursor.execute("SELECT * FROM clientes")
    clientes_rows = cursor.fetchall()

    cursor.execute("SELECT id, codigo, nombre, precio FROM productos")
    productos_data = cursor.fetchall()

    if not clientes_rows or not productos_data:
        print("❌ Faltan clientes o productos en la base de datos.")
        conexion.close()
        return

    estados_posibles = ['RECIBIDO', 'VALIDADO', 'PREPARADO', 'FACTURADO', 'ARMADO', 'CARGADO', 'EN_REPARTO', 'ENTREGADO', 'CERRADO']
    observaciones_posibles = [
        "Pedido tomado por agente comercial vía WhatsApp.",
        "Solicitud frecuente de reposición de stock de limpieza.",
        "Entrega coordinada en horario matutino.",
        "Cliente corporativo con cuenta corriente al día.",
        "Preventa realizada por agente de ruta zona Norte.",
        "Pedido de emergencia por alta demanda local."
    ]

    cantidad_pedidos = 100
    fecha_actual = datetime.now()

    print(f"⏳ Generando {cantidad_pedidos} pedidos y sus respectivos PDFs oficiales...")

    for _ in range(cantidad_pedidos):
        cliente_row = random.choice(clientes_rows)
        cliente_id = cliente_row["id"]
        cliente_dict = {
            "razon_social": cliente_row["razon_social"],
            "cuit": cliente_row["cuit"],
            "direccion": cliente_row["direccion_entrega"] if cliente_row["direccion_entrega"] else "N/D",
            "condicion_fiscal": cliente_row["condicion_fiscal"] if "condicion_fiscal" in cliente_row.keys() else "Responsable Inscripto"
        }

        dias_atras = random.randint(0, 90)
        fecha_pedido = fecha_actual - timedelta(days=dias_atras, hours=random.randint(1, 12), minutes=random.randint(0, 59))
        fecha_str = fecha_pedido.strftime('%Y-%m-%d %H:%M:%S')
        estado = random.choice(estados_posibles)
        observacion = random.choice(observaciones_posibles)

        # Insertar pedido
        cursor.execute("""
            INSERT INTO pedidos (cliente_id, fecha, estado, total, observaciones_agente)
            VALUES (?, ?, ?, 0, ?)
        """, (cliente_id, fecha_str, estado, observacion))
        
        pedido_id = cursor.lastrowid

        # Ítems aleatorios
        num_items = random.randint(1, 5)
        total_pedido = 0.0
        items_elegidos = random.sample(productos_data, min(num_items, len(productos_data)))
        items_pdf_data = []

        for prod_id, codigo, nombre, precio in items_elegidos:
            cantidad = random.randint(1, 10)
            subtotal = cantidad * precio
            total_pedido += subtotal

            cursor.execute("""
                INSERT INTO detalle_pedidos (pedido_id, producto_id, cantidad, precio_unitario)
                VALUES (?, ?, ?, ?)
            """, (pedido_id, prod_id, cantidad, precio))

            items_pdf_data.append([
                str(codigo),
                str(nombre),
                str(cantidad),
                f"${precio:,.2f}",
                f"${subtotal:,.2f}"
            ])

        # Actualizar total
        cursor.execute("UPDATE pedidos SET total = ? WHERE id = ?", (total_pedido, pedido_id))

        # GENERACIÓN DEL PDF OFICIAL CON EL ID EXACTO DEL PEDIDO
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

        info_data = [
            [Paragraph(f"<b>Nº de Orden:</b> <font color='#1e40af'>#{pedido_id}</font>", estilos['Normal']), Paragraph(f"<b>Fecha de Emisión:</b> {fecha_str}", estilos['Normal'])],
            [Paragraph(f"<b>Cliente / Razón Social:</b> {cliente_dict['razon_social']}", estilos['Normal']), Paragraph(f"<b>CUIT / Identificación:</b> {cliente_dict['cuit']}", estilos['Normal'])],
            [Paragraph(f"<b>Dirección de Destino:</b> {cliente_dict['direccion']}", estilos['Normal']), Paragraph(f"<b>Condición Fiscal:</b> {cliente_dict['condicion_fiscal']}", estilos['Normal'])]
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
        
        if observacion:
            elementos.append(Spacer(1, 10))
            obs_data = [[Paragraph(f"<b>Observaciones / Logística:</b> {observacion}", estilos['Normal'])]]
            t_obs = Table(obs_data, colWidths=[540])
            t_obs.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), color_fondo_tarjeta),
                ('PADDING', (0,0), (-1,-1), 8),
                ('BOX', (0,0), (-1,-1), 0.5, color_borde),
            ]))
            elementos.append(t_obs)

        doc.build(elementos)

    conexion.commit()
    conexion.close()
    print(f"🎉 ¡Proceso completado! Se generaron {cantidad_pedidos} pedidos con sus respectivos PDFs físicos en '{CARPETA_PDFS}'.")

if __name__ == "__main__":
    generar_datos_masivos()