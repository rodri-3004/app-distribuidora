# CONTEXTO.md · Distribuidora de productos de limpieza (sistema multiagente)

> Archivo de contexto del proyecto (versión 3). Todo asistente o agente que trabaje en este proyecto lo lee primero.
> Idioma de trabajo: español (código, nombres de tablas y mensajes).

## 1. Objetivo
Optimizar el ciclo de ventas de una distribuidora de productos de limpieza que hoy lo hace manualmente: pedido del cliente → validación → preparación → facturación → armado → carga al camión → entrega → cierre.

Es una **prueba piloto** pensada para un caso real. Se construye en dos tiempos:
1. **Plataforma piloto** (la "materia prima"): base de datos, API, tienda web y Mini-ERP. Se construye primero, en la PC, paso a paso y de forma visible.
2. **Agentes**: un Supervisor y subagentes que operan sobre esa plataforma a través de la API.

Los datos son **de prueba** por ahora, y están pensados para poder reemplazarse por los de la distribuidora más adelante.

## 2. Cómo se construye (regla de trabajo)
- La plataforma (Fase 0) se construye **paso a paso, en la PC de la persona**, con asistencia directa de la IA.
- La IA entrega el código en **partes chicas**, explica **qué hace y por qué**, y dice **cómo verificar** que funcionó.
- No se avanza al paso siguiente hasta que la persona confirma que el paso actual **se ve funcionando** (archivo de la base, página /docs de la API o navegador).
- Toda decisión de diseño que no esté en este archivo o en la especificación se avisa y se justifica.
- Los agentes se diseñan después: la persona define tarea, entradas, salidas y límites; la IA redacta el `.md` de cada agente; la persona lo revisa y lo prueba.

## 3. Glosario
- **Pedido:** compra confirmada por un cliente en la tienda.
- **Stock físico:** unidades que hay en el depósito.
- **Stock reservado:** unidades comprometidas por pedidos confirmados que todavía no se prepararon.
- **Stock disponible:** `stock_fisico - stock_reservado`.
- **Excepción:** situación que el sistema no resuelve solo; queda abierta hasta que una persona la resuelve.
- **Nivel 0:** la persona que supervisa, da órdenes en lenguaje natural y resuelve excepciones.
- **Estado de cuenta:** saldo de un cliente, calculado a partir de sus movimientos.

## 4. Arquitectura en tres capas
1. **Capa 1 · Plataforma piloto:** base de datos SQLite, API (FastAPI), tienda web y Mini-ERP (backoffice). Funciona a mano, sin IA.
2. **Capa 2 · Agentes (Paseo):** Supervisor + subagentes. Paseo trabaja sobre la misma carpeta del proyecto y los agentes llaman a la API local.
3. **Capa 3 · Torre de control:** módulo del Mini-ERP con estado de pedidos, cola de excepciones y consola del Nivel 0.

**Regla de oro:** los agentes NO acceden a la base de datos. Solo usan la API, cada uno con su identidad. La API valida permisos y transiciones de estado.

## 5. Estados del pedido
`RECIBIDO → VALIDADO → PREPARADO → FACTURADO → ARMADO → CARGADO → EN_REPARTO → ENTREGADO → CERRADO`

Cualquier etapa puede pasar a `EXCEPCION`. Un pedido no avanza de estado sin evidencia registrada. Las transiciones permitidas son solo las que van al estado siguiente (o a `EXCEPCION`).

## 6. Reglas de negocio (iniciales)
- **R1 · Precio:** si el precio del pedido difiere del vigente, el pedido queda observado y no se corrige solo.
- **R2 · Stock:** disponible = físico − reservado. Si falta, se propone entrega parcial solo con aprobación del Nivel 0.
- **R3 · Crédito:** el cliente debe estar `ACTIVO` y `saldo_actual + total` no puede superar `limite_credito`; si no, excepción.
- **R4 · Facturación:** solo se factura un pedido preparado y con los faltantes resueltos.
- **R5 · Cuenta corriente:** al emitir la factura se registra un movimiento y sube el saldo; un pago cargado en el Mini-ERP lo baja.
- **R6 · Cambios masivos:** siempre en dos pasos (vista previa y aplicación), con confirmación del Nivel 0 e historial reversible.
- **R7 · Excepciones:** toda excepción tiene motivo y queda abierta hasta que una persona la resuelve.
- **R8 · Acceso y trazabilidad:** solo por API con identidad de agente; cada acción deja un evento con evidencia.

## 7. Qué le pasa al stock
| Momento | Efecto |
|---|---|
| Cliente confirma el pedido | Se reserva la cantidad si alcanza (dentro de una transacción). Si no alcanza, no se puede confirmar. |
| Pedido validado | Sin cambios. |
| Pedido rechazado o cancelado | Se libera la reserva. |
| Preparación del picking | Se descuenta del físico y de lo reservado. Si hay faltante, se registra y se abre una excepción. |

## 8. Decisiones del proyecto (recomendadas, a confirmar)
- **D1 · Canal de entrada:** primero API; el mail se suma en la Fase 5 como integración real.
- **D2 · Validadores:** dos agentes separados (precios y stock / crédito).
- **D3 · Gestor de precios y stock:** incluido (flujo de órdenes del Nivel 0).
- **D4 · Precio distinto del vigente:** el pedido queda observado y decide el Nivel 0.
- **D5 · Faltante de stock:** entrega parcial solo con aprobación del Nivel 0.
- **D6 · Tienda mínima:** selector de cliente, imágenes locales genéricas, sin pagos online.
- **D7 · Datos del piloto:** de prueba al inicio; reales de la distribuidora más adelante.

## 9. Base de datos (14 tablas)
`usuarios`, `clientes`, `movimientos_cuenta`, `productos`, `precios_historial`, `pedidos`, `detalle_pedidos`, `facturas`, `armados`, `camiones`, `rutas_paradas`, `entregas`, `eventos_log`, `excepciones`.

La especificación campo por campo está en el Anexo A del documento "Plan A integrado v3". Si hay que cambiarla, avisar antes de modificar.

## 10. Convenciones
- Nombres de tablas y campos en español, en `snake_case`, tal como figuran en la especificación.
- Estados y tipos en MAYÚSCULAS (`ACTIVO`, `EN_REPARTO`).
- Montos en pesos, con dos decimales.

## 11. Estructura de carpetas (propuesta)
```
distribuidora-ia/
├── CONTEXTO.md
├── base_datos/       # creación de tablas y datos de prueba (SQLite)
├── api/              # API (FastAPI)
├── web/              # tienda y Mini-ERP
├── agentes/          # un archivo .md por agente (desde la Fase 1)
├── casos_de_prueba/  # casos con resultado esperado
└── bitacora.md       # qué se pidió a la IA, qué falló y cómo se resolvió
```

## 12. Cómo correr y probar
_Se completa al terminar cada paso, con los comandos reales que se usaron para crear la base, cargar datos de prueba, levantar la API y abrir la tienda._

## 13. Fase actual
**Fase 0.1 · Base de datos (SQLite) y datos de prueba.** Todavía sin API, tienda ni agentes.
