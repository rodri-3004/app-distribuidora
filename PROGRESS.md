# PROGRESS.md · Memoria del Supervisor

> Este archivo guarda las notas de la última sesión de trabajo.
> El Supervisor DEBE leerlo al empezar a operar y actualizarlo al terminar.

## Estado actual de la sesión
- **Fecha:** 2026-11-11
- **Pedidos procesados en esta sesión:** [3325, 3326, 3327]
- **Pedidos en excepción:** [] (sin excepciones abiertas)
- **Último pedido trabajado:** 3327 (estado final: `CANCELADO`)

## Notas para la próxima sesión
- **Prueba de los 5 casos: COMPLETADA.** Casos cubiertos: happy path, crédito excedido/bloqueado, sin stock, precio cambiado y cliente bloqueado por deuda. Los sensores frenaron el flujo en cada caso sin intervención automática.
- **Cierre de la prueba en lote (3 sensores):**
  - **#3325 — Sin Stock:** excepción #4 (`PRECIO`) resuelta. Pedido cancelado. Producto `214`: `stock_reservado` **699 → 63** (−636), `stock_disponible` **0 → 636**, `stock_fisico` sin cambios (699).
  - **#3326 — Precio Cambiado:** excepción #5 (`PRECIO`) resuelta. Pedido cancelado. Producto `213`: `stock_reservado` **60 → 59** (−1), `stock_disponible` **893 → 894**, `stock_fisico` sin cambios (953).
  - **#3327 — Cliente Bloqueado:** excepción #6 (`CREDITO`) resuelta. Pedido cancelado. Producto `165`: `stock_reservado` **42 → 41** (−1), `stock_disponible` **765 → 766**, `stock_fisico` sin cambios (807).
- **Saldos restituidos:**
  - Cliente `146`: `$1.547.300 → $80.400` (se descontaron los totales de #3325 `$1.462.800` y #3326 `$4.100`).
  - Cliente `3`: `$114.850 → $110.000` (se descontó el total de #3327 `$4.850`).
- **Estados finales:** #3325, #3326 y #3327 quedaron en `CANCELADO` (`estado_anterior: EXCEPCION`).
- **Excepciones:** `PATCH /excepciones/4/resolver`, `5` y `6` → `200 {"mensaje": "Excepción resuelta."}`. `GET /excepciones` devuelve `[]`.
- **Bases limpias:** sin excepciones abiertas, stock físico intacto, stock reservado liberado y saldos de clientes restituidos. No se tocaron los demás pedidos de la base.
- **Sensor pendiente (arrastre):** `python check.py` sigue fallando por el texto de prueba de `check.py` (`VEREDICTO: OK` vs. `✅ APROBADO` que exige `agents/validar_salida.py`).

---

## Historial de Sesiones
*(El Supervisor puede ir agregando un resumen acá al final de cada día)*
- **Sesión 0 (Setup):** Harness construido. Base de datos limpia. Sensores listos. Pendiente de primera prueba en Paseo.
- **Sesión 1 (2026-11-08):** Se ejecutó `check.py`: el test de integración pasó y limpió sus datos, pero el validador de salida falló por el formato del texto de prueba (`OK` vs. `✅ APROBADO`). Se cerraron los pedidos 3317 y 3316 (`ENTREGADO → CERRADO`) y se confirmó que `GET /pedidos?estado=ENTREGADO` devuelve `[]`.
- **Sesión 2 (2026-11-08):** Prueba de estrés de sensores exitosa. El pedido 3320 se detuvo solo en el `validador_credito` y generó la excepción #3. La excepción se resolvió manualmente y el Nivel 0 decidió cancelar el pedido. Estado final: `CANCELADO`; stock reservado del producto 165 restituido (42 → 41) y saldo del cliente 145 restituido (4850 → 0). Sin excepciones abiertas.
- **Sesión 3 (2026-11-11):** Prueba en lote de los 3 sensores. Pedidos 3325 (sin stock), 3326 (precio cambiado) y 3327 (cliente bloqueado) recorrieron el Comando 1 y se detuvieron solos: #3325 y #3326 en `validador_precios`, #3327 en `validador_credito`. Los 3 quedaron en `EXCEPCION` y se registraron las excepciones #4, #5 y #6 más los eventos #3, #4 y #5.
- **Sesión 4 (2026-11-11):** Cierre de la prueba de los 5 casos. Se resolvieron las excepciones #4, #5 y #6 y se cancelaron los pedidos 3325, 3326 y 3327. Stock reservado liberado y saldos restituidos. `GET /excepciones` → `[]`. Sin excepciones abiertas.
