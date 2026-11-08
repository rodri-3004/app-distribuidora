# PROGRESS.md · Memoria del Supervisor

> Este archivo guarda las notas de la última sesión de trabajo.
> El Supervisor DEBE leerlo al empezar a operar y actualizarlo al terminar.

## Estado actual de la sesión
- **Fecha:** 2026-11-08
- **Pedidos procesados en esta sesión:** [3320]
- **Pedidos en excepción:** [] (sin excepciones abiertas)
- **Último pedido trabajado:** 3320 (estado final: `CANCELADO`)

## Notas para la próxima sesión
- **Prueba de estrés de sensores: ÉXITO TOTAL.** Se creó el pedido **3320** para el cliente **145** (`Autoservicio Express 241`, `limite_credito = 0.0`) con 1 unidad del producto **165** (Jabón Líquido para Ropa Ala 3L, `$4.850`). El flujo se detuvo solo en el `validador_credito` porque `saldo_actual (4850.0) + total (4850.0) = 9700.0 > limite_credito (0.0)`.
- **Excepción #3 (`CREDITO`) resuelta manualmente** con `PATCH /excepciones/3/resolver`.
- **Cierre definitivo:** por decisión del Nivel 0, el pedido **3320** fue cancelado con `PATCH /pedidos/3320/estado` → `200 {"mensaje": "Estado: Cancelado", "nuevo_estado": "CANCELADO"}`. Transición `EXCEPCION → CANCELADO` permitida por la API.
- **Verificación final:**
  - Pedido 3320: estado `CANCELADO`, `estado_anterior: "EXCEPCION"`.
  - Producto 165: `stock_fisico` 807 (sin cambios), `stock_reservado` **42 → 41** (volvió a su valor original), `stock_disponible` 765 → 766.
  - Cliente 145: `saldo_actual` **4850.0 → 0.0** (se liberó el saldo del pedido cancelado).
  - `GET /excepciones` → `[]`. No hay excepciones abiertas.
- **Observación de API:** `GET /pedidos/{id}` devuelve `cliente` sin el campo `estado`; el validador de crédito no puede verificar `ACTIVO` desde ese endpoint. El corte igual funciona por la regla de límite de crédito.
- **Sensor pendiente (arrastre):** `python check.py` sigue fallando por el texto de prueba de `check.py` (`VEREDICTO: OK` vs. `✅ APROBADO` que exige `agents/validar_salida.py`).

---

## Historial de Sesiones
*(El Supervisor puede ir agregando un resumen acá al final de cada día)*
- **Sesión 0 (Setup):** Harness construido. Base de datos limpia. Sensores listos. Pendiente de primera prueba en Paseo.
- **Sesión 1 (2026-11-08):** Se ejecutó `check.py`: el test de integración pasó y limpió sus datos, pero el validador de salida falló por el formato del texto de prueba (`OK` vs. `✅ APROBADO`). Se cerraron los pedidos 3317 y 3316 (`ENTREGADO → CERRADO`) y se confirmó que `GET /pedidos?estado=ENTREGADO` devuelve `[]`.
- **Sesión 2 (2026-11-08):** Prueba de estrés de sensores exitosa. El pedido 3320 se detuvo solo en el `validador_credito` y generó la excepción #3. La excepción se resolvió manualmente y el Nivel 0 decidió cancelar el pedido. Estado final: `CANCELADO`; stock reservado del producto 165 restituido (42 → 41) y saldo del cliente 145 restituido (4850 → 0). Sin excepciones abiertas.
