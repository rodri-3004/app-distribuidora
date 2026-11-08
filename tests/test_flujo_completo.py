import requests
import sys
import time
import sqlite3
from pathlib import Path

# URL base de tu API local
BASE_URL = "http://127.0.0.1:8001"

# Ruta a la base de datos
RUTA_DB = Path(__file__).parent.parent / "base_datos" / "distribuidora.db"
if not RUTA_DB.exists():
    RUTA_DB = Path(__file__).parent.parent / "api" / "distribuidora.db"

def log(mensaje, exito=True):
    prefijo = "✅" if exito else "❌"
    print(f"{prefijo} {mensaje}")
    if not exito:
        sys.exit(1)

def obtener_token(email, clave):
    res = requests.post(f"{BASE_URL}/login", json={"email": email, "clave": clave})
    if res.status_code != 200:
        log(f"Error de login para {email}: {res.text}", False)
    return res.json()["access_token"]

def limpiar_pedido_de_prueba(pedido_id, producto_id, cantidad, stock_inicial):
    """Limpia la base de datos y el stock después de la prueba."""
    print("\n🧹 Limpiando datos de la prueba...")
    try:
        conexion = sqlite3.connect(RUTA_DB)
        cursor = conexion.cursor()
        
        # 1. Borrar detalles del pedido
        cursor.execute("DELETE FROM detalle_pedidos WHERE pedido_id = ?", (pedido_id,))
        # 2. Borrar historial
        cursor.execute("DELETE FROM pedido_historial_estados WHERE pedido_id = ?", (pedido_id,))
        # 3. Borrar factura (si se creó)
        cursor.execute("DELETE FROM facturas WHERE pedido_id = ?", (pedido_id,))
        # 4. Borrar movimientos de cuenta
        cursor.execute("DELETE FROM movimientos_cuenta WHERE pedido_id = ?", (pedido_id,))
        # 5. Borrar armado (si se creó)
        cursor.execute("DELETE FROM armados WHERE pedido_id = ?", (pedido_id,))
        # 6. Borrar paradas de ruta y entregas
        cursor.execute("SELECT id FROM rutas_paradas WHERE pedido_id = ?", (pedido_id,))
        paradas = cursor.fetchall()
        for p in paradas:
            cursor.execute("DELETE FROM entregas WHERE parada_id = ?", (p[0],))
        cursor.execute("DELETE FROM rutas_paradas WHERE pedido_id = ?", (pedido_id,))
        # 7. Borrar el pedido final
        cursor.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
        
        # 8. Restaurar el stock físico del producto
        cursor.execute("UPDATE productos SET stock_fisico = ? WHERE id = ?", (stock_inicial, producto_id))
        
        conexion.commit()
        conexion.close()
        print("✅ Base de datos y stock restaurados a su estado original.")
    except Exception as e:
        print(f"⚠️ Error al limpiar la base de datos: {e}. (El pedido de prueba quedó en la base).")

def test_flujo_completo():
    print("\n🚀 INICIANDO TEST DE INTEGRACIÓN (HAPPY PATH)\n")
    
    # 1. Login del Supervisor (Admin)
    token = obtener_token("supervisor@distribuidora.com", "Super123!")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    log("Login del Supervisor exitoso.")

    # 2. Obtener un producto y un cliente para el pedido
    res_prods = requests.get(f"{BASE_URL}/productos", headers=headers)
    productos = [p for p in res_prods.json() if p["stock_disponible"] > 10]
    if not productos:
        log("No hay productos con stock suficiente para el test.", False)
    
    prod = productos[0]
    stock_fisico_inicial = prod["stock_fisico"]
    cantidad_a_comprar = 5

    res_clientes = requests.get(f"{BASE_URL}/clientes", headers=headers)
    clientes = [c for c in res_clientes.json() if c["estado"] == "ACTIVO"]
    if not clientes:
        log("No hay clientes ACTIVOS para el test.", False)
    
    cliente = clientes[0]
    log(f"Producto elegido: {prod['nombre']} (Stock inicial: {stock_fisico_inicial})")
    log(f"Cliente elegido: {cliente['razon_social']}")

    # 3. Crear el pedido
    payload_pedido = {
        "cliente_id": cliente["id"],
        "items": [{"producto_id": prod["id"], "cantidad": cantidad_a_comprar}]
    }
    res_pedido = requests.post(f"{BASE_URL}/pedidos", json=payload_pedido, headers=headers)
    if res_pedido.status_code != 200:
        log(f"Error al crear pedido: {res_pedido.text}", False)
    
    pedido_id = res_pedido.json()["pedido_id"]
    log(f"Pedido #{pedido_id} creado en estado RECIBIDO.")

    # 4. Avanzar por todos los estados manualmente
    estados_flujo = [
        "VALIDADO", 
        "PREPARADO", 
        "FACTURADO", 
        "ARMADO", 
        "CARGADO", 
        "EN_REPARTO", 
        "ENTREGADO", 
        "CERRADO"
    ]

    for estado in estados_flujo:
        time.sleep(0.5) # Pequeña pausa para no saturar la API
        if estado == "FACTURADO":
            res = requests.post(f"{BASE_URL}/pedidos/{pedido_id}/facturar", headers=headers)
        elif estado == "ARMADO":
            res = requests.post(f"{BASE_URL}/pedidos/{pedido_id}/armar", json={"bultos": 1, "resultado": "OK"}, headers=headers)
        elif estado == "ENTREGADO":
            res = requests.post(f"{BASE_URL}/entregas/{pedido_id}", json={"receptor": "Test Bot", "resultado": "ENTREGADO"}, headers=headers)
        else:
            res = requests.patch(f"{BASE_URL}/pedidos/{pedido_id}/estado", json={"nuevo_estado": estado}, headers=headers)
        
        if res.status_code not in [200, 201]:
            log(f"Error al avanzar a {estado}: {res.text}", False)
        log(f"Estado cambiado a: {estado}")

    # 5. VERIFICACIONES FINALES (El "Sensor")
    print("\n🔍 VERIFICANDO RESULTADOS FINALES...")
    
    # A. Verificar estado del pedido
    res_estado = requests.get(f"{BASE_URL}/pedidos/{pedido_id}", headers=headers)
    pedido_final = res_estado.json()
    if pedido_final["estado"] == "CERRADO":
        log("El pedido terminó en estado CERRADO.")
    else:
        log(f"El pedido quedó en {pedido_final['estado']} en vez de CERRADO.", False)

    # B. Verificar stock físico (debería haber bajado)
    res_prods_final = requests.get(f"{BASE_URL}/productos", headers=headers)
    prod_final = next((p for p in res_prods_final.json() if p["id"] == prod["id"]), None)
    
    if not prod_final:
        log("No se encontró el producto en la verificación final.", False)

    stock_esperado = stock_fisico_inicial - cantidad_a_comprar
    if prod_final["stock_fisico"] == stock_esperado:
        log(f"Stock físico descontado correctamente: {stock_fisico_inicial} -> {prod_final['stock_fisico']}")
    else:
        log(f"Error en stock. Esperado: {stock_esperado}, Real: {prod_final['stock_fisico']}", False)

    # C. Verificar stock reservado (debería ser 0, porque ya se preparó)
    if prod_final["stock_reservado"] == prod["stock_reservado"]:
        log(f"Stock reservado volvió a 0 correctamente.")
    else:
        log(f"Error en stock reservado. Quedó en {prod_final['stock_reservado']}", False)

    # 6. LIMPIEZA (El paso nuevo que borra todo)
    limpiar_pedido_de_prueba(pedido_id, prod["id"], cantidad_a_comprar, stock_fisico_inicial)

    print("\n🎉 TEST COMPLETADO CON ÉXITO. El flujo y el stock están perfectos.\n")

if __name__ == "__main__":
    try:
        test_flujo_completo()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: No se pudo conectar a la API. Asegurate de que uvicorn esté corriendo en el puerto 8001.\n")
        sys.exit(1)