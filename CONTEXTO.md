# CONTEXTO.md · Distribuidora de productos de limpieza (sistema multiagente)

> Archivo de contexto del proyecto (versión 4.3). Todo asistente o agente que trabaje en este proyecto lo lee primero.
> Idioma de trabajo: español (código, nombres de tablas y mensajes).

## 1. Objetivo
Optimizar el ciclo de ventas de una distribuidora de productos de limpieza que hoy lo hace manualmente: pedido del cliente → validación → preparación → facturación → armado → carga al camión → entrega → cierre.

Es una **prueba piloto** pensada para un caso real. La plataforma base ya está construida y funcional. Los agentes de IA (en Paseo.sh) operarán sobre esta plataforma para automatizar el flujo.

## 2. Cómo se construyó (regla de trabajo)
- La plataforma se construyó **paso a paso, en la PC de la persona**, con asistencia directa de la IA.
- Cada paso se verificó visualmente antes de avanzar (web, base de datos o `/docs`).
- Toda decisión de diseño se documentó y se justificó.
- Los agentes se diseñan ahora: la persona define tarea, entradas, salidas y límites; la IA redacta el `.md` de cada agente; la persona lo revisa y lo prueba.

## 3. Glosario
- **Usuario:** quien inicia sesión en la web. Puede ser `admin`, `cliente` o `agente`.
- **Cliente:** comercio o persona que recibe el pedido. Cada cliente tiene un dueño (`clientes.usuario_dueno`).
- **Pedido:** compra confirmada por un usuario para un cliente.
- **Stock físico:** unidades que hay en el depósito.
- **Stock reservado:** unidades comprometidas por pedidos `RECIBIDO` o `VALIDADO` que todavía no se prepararon.
- **Stock disponible:** `stock_fisico - stock_reservado`. Es lo que ve la tienda.
- **Alerta Silenciosa:** registro en la tabla `alertas_stock` cuando un producto baja del `stock_minimo` (default 50). El agente de stock las consulta y avisa al humano.
- **Excepción:** situación que el sistema no resuelve solo; queda abierta hasta que una persona la resuelve.
- **Nivel 0:** la persona que supervisa, da órdenes en lenguaje natural y resuelve excepciones.
- **Agente Simulador:** un usuario con rol `admin` que simula al operario (armado) y al chofer (entrega). Se elimina en producción.
- **Harness:** el entorno completo (guías + sensores) que permite a los agentes operar de forma segura y verificable.

## 4. Arquitectura en tres capas
1. **Capa 1 · Plataforma piloto:** SQLite, API (FastAPI), tienda web (React) y Mini-ERP. Funciona a mano, sin IA.
2. **Capa 2 · Agentes (Paseo):** Supervisor + subagentes. Paseo trabaja sobre la misma carpeta del proyecto y los agentes llaman a la API local.
3. **Capa 3 · Torre de control:** la vista de pedidos en la web, con estado, seguimiento y alertas.

**Regla de oro:** los agentes NO acceden a la base de datos. Solo usan la API, cada uno con su identidad (token JWT). La API valida permisos y transiciones de estado.

### Usuarios, sesión y separación de datos
- Cada usuario ve **solo** sus clientes y su historial de pedidos. Los productos y el stock son globales.
- Roles actuales: `admin`, `cliente` y `agente`.
- Sesión: el login devuelve un **token JWT** (`access_token`, vence a las 8 horas). Los endpoints protegidos usan la dependencia `usuario_actual`.
- Las contraseñas se guardan con **bcrypt**.
- Los agentes se crearon con la tabla `usuarios` actualizada para aceptar el rol `'agente'`. Cada agente tiene su propia cuenta de correo (ej. `recepcionista@distribuidora.com`) para que los logs de trazabilidad sean correctos.

## 5. Estados del pedido
`RECIBIDO → VALIDADO → PREPARADO → FACTURADO → ARMADO → CARGADO → EN_REPARTO → ENTREGADO → CERRADO`

- `EXCEPCION`: cualquier etapa puede pasar a este estado; una persona lo resuelve.
- `CANCELADO`: solo desde `RECIBIDO` o `VALIDADO` (libera la reserva).
- Cada cambio de estado se registra en la tabla `pedido_historial_estados` con fecha, autor y evidencia.

### Traducción de estados para la web
- `RECIBIDO` → "Pendiente"
- `VALIDADO`, `PREPARADO`, `FACTURADO` → "En preparación"
- `ARMADO`, `CARGADO` → "Preparado para despachar"
- `EN_REPARTO` → "Pedido en camino"
- `ENTREGADO`, `CERRADO` → "Pedido entregado"
- `EXCEPCION` → "En revisión"
- `CANCELADO` → "Cancelado"

## 6. Reglas de negocio
- **R1 · Precio:** si el precio del pedido difiere del vigente, el pedido queda observado y no se corrige solo.
- **R2 · Stock:** disponible = físico − reservado. Si el producto baja de su `stock_minimo`, se genera una alerta silenciosa en `alertas_stock`.
- **R3 · Crédito:** el cliente debe estar `ACTIVO` y `saldo_actual + total` no puede superar `limite_credito`; si no, excepción.
- **R4 · Facturación:** solo se factura un pedido `PREPARADO`.
- **R5 · Cuenta corriente:** al emitir la factura se registra un movimiento y sube el saldo; un pago cargado lo baja.
- **R6 · Cambios masivos:** siempre en dos pasos (vista previa y aplicación), con confirmación del Nivel 0 e historial reversible.
- **R7 · Excepciones:** toda excepción tiene motivo y queda abierta hasta que una persona la resuelve.
- **R8 · Acceso y trazabilidad:** solo por API con identidad; cada acción deja un evento con evidencia en `pedido_historial_estados` y en `eventos_log`.
- **R9 · Separación de datos:** cada usuario ve solo sus clientes y sus pedidos; admin y agentes ven todo. **Los clientes no pueden modificar ni ver pedidos ajenos (validado en API).**
- **R10 · Planillas:** el stock y el saldo de una planilla solo se usan al **crear** el producto o el cliente. Reimportar nunca pisa el stock ni el saldo reales.
- **R11 · Alertas silenciosas:** cuando un producto baja de su `stock_minimo`, se genera un registro en `alertas_stock`. El agente de stock debe consultarlas y resolverlas.

## 7. Qué le pasa al stock (modelo de reserva)
| Momento | Físico | Reservado |
|---|---|---|
| Se confirma el pedido (`POST /pedidos`) | sin cambio | + cantidad (solo si alcanza el disponible; si no, error 400) |
| Se prepara (`POST /pedidos/{id}/estado` con estado `PREPARADO`) | − cantidad | − cantidad |
| Se cancela estando `RECIBIDO` o `VALIDADO` | sin cambio | − cantidad |

**Control de consistencia:** `stock_reservado` de cada producto debe ser igual a las unidades de sus pedidos en `RECIBIDO` o `VALIDADO`. Si hay diferencias, ejecutar `base_datos/reconciliar_stock.py`.

## 8. Decisiones del proyecto
- **D1 · Canal de entrada:** primero API; el mail se suma al final como integración real.
- **D2 · Validadores:** dos agentes separados (precios/stock y crédito).
- **D3 · Gestor de precios y stock:** incluido (flujo de órdenes del Nivel 0 por planilla).
- **D4 · Precio distinto del vigente:** el pedido queda observado y decide el Nivel 0.
- **D5 · Faltante de stock:** entrega parcial solo con aprobación del Nivel 0.
- **D6 · Tienda:** login con sesión propia; el checkout permite elegir un cliente guardado o cargar los datos a mano.
- **D7 · Datos del piloto:** de prueba al inicio, desde planillas; reales de la distribuidora más adelante.
- **D8 · Un CUIT/DNI = un cliente = un dueño.**
- **D9 · Stock con reserva** (decidido e implementado).
- **D10 · Simulación de operario y chofer:** como el piloto no tiene personas reales en esos roles, se creó un **Agente Simulador** con rol `admin` que ejecuta los endpoints de armar y entregar. En el harness de Paseo, este agente está representado por el archivo `simulador_humano.md`. Los archivos `controlador_armado.md` y `seguimiento.md` quedan inactivos en el piloto y se activan en producción.
- **D11 · IVA en facturación:** el precio del producto en el pedido es el subtotal. Al facturar (`POST /pedidos/{id}/facturar`), la API calcula el 21% de IVA y lo suma al total de la factura. El pedido guarda el total sin IVA, y la factura el total con IVA. (Si en producción los precios de lista incluyen IVA, esta lógica deberá invertirse).

## 9. Base de datos (16 tablas)
Tablas del plan: `usuarios`, `clientes`, `movimientos_cuenta`, `productos`, `precios_historial`, `pedidos`, `detalle_pedidos`, `facturas`, `armados`, `camiones`, `rutas_paradas`, `entregas`, `eventos_log`, `excepciones`.

Tablas agregadas en la implementación:
- `pedido_historial_estados`: registra cada cambio de estado con fecha y autor.
- `alertas_stock`: registra productos con stock por debajo del mínimo.

Columnas agregadas respecto de la especificación original: `clientes.usuario_dueno`, `clientes.telefono`, `clientes.condicion_fiscal`, `clientes.medio_pago`, `productos.categoria`, `productos.imagen_url`, `productos.stock_minimo`, `pedidos.usuario_id`, `pedidos.fecha_entrega`, `pedidos.estado_anterior`.

## 10. Planillas de datos
- `clientes.xlsx` y `productos.xlsx` (hoja `clientes` / `productos`, más una hoja "Instrucciones").
- Se cargan con `importar_excel.py` o con los endpoints `/clientes/importar-excel` y `/productos/importar-excel`.
- Clave de cada planilla: `cuit` (clientes) y `codigo` (productos).
- El endpoint de productos solo actualiza precios (R10).

## 11. Convenciones
- Nombres de tablas y campos en español, `snake_case`.
- Estados y tipos en MAYÚSCULAS (`ACTIVO`, `EN_REPARTO`).
- Montos en pesos, con dos decimales.

## 12. Estructura de carpetas
APP-DISTRIBUIDORA-PROCESOS/
├── CONTEXTO.md
├── base_datos/
│ ├── crear_base.py
│ ├── agregar_historial_estados.py
│ ├── agregar_rol_agente.py
│ ├── agregar_tabla_alertas.py
│ ├── cargar_camiones.py
│ ├── crear_agentes_paseo.py
│ ├── crear_simulador.py
│ ├── reconciliar_stock.py
│ ├── distribuir_fechas_entrega.py
│ ├── resetear_pedidos_a_pendientes.py
│ └── distribuidora.db
├── api/
│ └── main.py (FastAPI)
├── frontend/
│ ├── src/
│ │ ├── App.tsx
│ │ ├── AuthView.tsx
│ │ ├── App.css
│ │ └── index.css
│ └── package.json
├── agentes/
│ ├── supervisor.md
│ ├── playbook.md
│ ├── recepcionista.md
│ ├── validador_precios.md
│ ├── validador_credito.md
│ ├── preparador.md
│ ├── facturador.md
│ ├── controlador_armado.md (inactivo en piloto)
│ ├── planificador.md
│ ├── seguimiento.md (inactivo en piloto)
│ ├── auditor.md
│ ├── registro.md
│ ├── gestor_precios.md
│ ├── reposicion.md
│ ├── simulador_humano.md
│ └── validar_salida.py
├── tests/
│ └── test_flujo_completo.py
├── documentos_pedidos/
├── clientes.xlsx
├── productos.xlsx
├── importar_excel.py
└── bitacora.md

## 13. Endpoints de la API

### Autenticación
- `POST /registro`, `POST /activar`, `POST /login`, `GET /yo`
- `POST /recuperar-password`, `POST /resetear-password`, `POST /cambiar-password`

### Productos y Clientes
- `GET /productos`, `GET /categorias`, `POST /productos/importar-excel`
- `GET /clientes`, `POST /clientes`, `POST /clientes/importar-excel`, `PUT /clientes/{id}`, `DELETE /clientes/{id}`

### Pedidos
- `POST /pedidos`, `PATCH /pedidos/{id}/estado`, `GET /pedidos/{id}/seguimiento`, `GET /pedidos/todos`
- `GET /pedidos?estado={estado}`, `GET /pedidos/{id}`, `GET /pedidos/entrega/{fecha}`
- `POST /pedidos/{id}/asignar-fecha`
- `GET /pedidos/{id}/factura`, `GET /pedidos/{id}/entrega`

### Logística
- `POST /pedidos/{id}/facturar`
- `POST /pedidos/{id}/armar`
- `POST /rutas/planificar`
- `POST /entregas/{id}`

### Excepciones
- `POST /excepciones`
- `GET /excepciones`
- `PATCH /excepciones/{id}/resolver`

### Alertas de Stock
- `GET /alertas-stock/pendientes`
- `PATCH /alertas-stock/{id}/resolver`

### Eventos
- `POST /eventos`

## 14. Cómo correr y probar
- Instalar dependencias de la API: `pip install fastapi uvicorn pandas openpyxl reportlab email-validator python-multipart pyjwt bcrypt`
- API: `uvicorn main:app --reload --port 8001` desde la carpeta `api` (documentación en `http://127.0.0.1:8001/docs`).
- Frontend: `npm run dev` desde `frontend` (`http://localhost:5173`).
- Ejecutar tests de integración: `python tests/test_flujo_completo.py` (con la API corriendo).
- Reiniciar datos de prueba: `python base_datos/resetear_pedidos_a_pendientes.py` y luego `python base_datos/reconciliar_stock.py`.

## 15. Fase actual
**Fase 1 · Agentes en Paseo.sh.** La plataforma está 100% completa y funcional. Las identidades de los 13 agentes están creadas (12 agentes + 1 simulador). Los archivos `.md` de instrucciones están en la carpeta `agentes/`, incluyendo el `playbook.md`. El harness cuenta con sensores (test de integración y validador de salida). El siguiente paso es abrir Paseo.sh, cargar la carpeta del proyecto y darle la orden al Supervisor para que empiece a operar.

## 16. Seguridad: notas del piloto local
- `/recuperar-password` y `/registro` devuelven el código en la respuesta (`token_debug`) y `/activar` no verifica el código: aceptable solo en la PC local; resolver antes de usar datos reales.
- Los nombres de dueño son texto (`usuario_dueno`), sin clave foránea.
- El agente simulador tiene rol `admin` para poder hacer de operario y chofer. En producción, se elimina.
- **Validaciones de API:** Se agregaron chequeos para que los clientes no puedan ver pedidos ajenos, modificar clientes de otros dueños o crear pedidos a nombre de otros. Los agentes y admins tienen acceso total.
- **Claves de agentes:** Las claves de los agentes están definidas en el script `base_datos/crear_agentes_paseo.py` (ej. `Super123!`, `Recepcion123!`, etc.) y encriptadas en la base de datos con bcrypt.
