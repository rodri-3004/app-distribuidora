import requests
import sys
import time

# URL base de tu API local
BASE_URL = "http://127.0.0.1:8001"

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
            # Para facturar hay un endpoint específico
            res = requests.post(f"{BASE_URL}/pedidos/{pedido_id}/facturar", headers=headers)
        elif estado == "ARMADO":
            # Para armar hay un endpoint específico
            res = requests.post(f"{BASE_URL}/pedidos/{pedido_id}/armar", json={"bultos": 1, "resultado": "OK"}, headers=headers)
        elif estado == "ENTREGADO":
            # Para entregar se usa el endpoint de entregas
            res = requests.post(f"{BASE_URL}/entregas/{pedido_id}", json={"receptor": "Test Bot", "resultado": "ENTREGADO"}, headers=headers)
        else:
            # El resto de estados se cambian con el PATCH genérico
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
    if prod_final["stock_reservado"] == prod["stock_reservado"]: # Debería volver a su estado original
        log(f"Stock reservado volvió a 0 correctamente.")
    else:
        log(f"Error en stock reservado. Quedó en {prod_final['stock_reservado']}", False)

    print("\n🎉 TEST COMPLETADO CON ÉXITO. El flujo y el stock están perfectos.\n")

if __name__ == "__main__":
    try:
        test_flujo_completo()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: No se pudo conectar a la API. Asegurate de que uvicorn esté corriendo en el puerto 8001.\n")
        sys.exit(1)