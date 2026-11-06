"""
Agrega el estado CANCELADO a los estados permitidos de los pedidos.

Por qué hace falta: la tabla pedidos tiene una restricción (CHECK) con la lista de estados válidos,
y CANCELADO no figura. Por eso el endpoint /pedidos/{id}/cancelar falla con error 500.
SQLite no permite modificar un CHECK, así que se recrea la tabla pedidos con los mismos datos.

Ubicación: base_datos/agregar_estado_cancelado.py (al lado de distribuidora.db).
Ejecutar con la API detenida:  python base_datos/agregar_estado_cancelado.py
Se puede ejecutar más de una vez sin romper nada.
"""
import re
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

RUTA_DB = Path(__file__).parent / "distribuidora.db"


def migrar():
    if not RUTA_DB.exists():
        raise FileNotFoundError(f"No se encontró la base en {RUTA_DB}")

    con = sqlite3.connect(RUTA_DB, isolation_level=None)
    sql = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='pedidos'").fetchone()[0]
    if "'CANCELADO'" in sql:
        print("La tabla pedidos ya permite el estado CANCELADO. No hay nada que hacer.")
        con.close()
        return

    # Los índices o triggers propios de pedidos se perderían al recrear la tabla: mejor frenar
    extras = con.execute("""SELECT name FROM sqlite_master
                            WHERE tbl_name='pedidos' AND type IN ('index','trigger') AND sql IS NOT NULL""").fetchall()
    if extras:
        raise RuntimeError(f"pedidos tiene índices o triggers propios que habría que recrear: {extras}")

    if "'EXCEPCION')" not in sql:
        raise RuntimeError("No reconozco la restricción de estados de pedidos; no se modificó nada.")

    copia = RUTA_DB.with_name(f"distribuidora_respaldo_{datetime.now():%Y%m%d_%H%M%S}.db")
    con.close()
    shutil.copy(RUTA_DB, copia)
    print(f"Respaldo creado: {copia.name}")

    nuevo_sql = sql.replace("'EXCEPCION')", "'EXCEPCION', 'CANCELADO')")
    nuevo_sql = re.sub(r'CREATE TABLE (IF NOT EXISTS )?["`]?pedidos["`]?', "CREATE TABLE pedidos_nueva", nuevo_sql, count=1)

    con = sqlite3.connect(RUTA_DB, isolation_level=None)
    con.execute("PRAGMA foreign_keys = OFF")  # necesario para recrear una tabla referenciada por otras
    cur = con.cursor()
    cur.execute("BEGIN")
    try:
        cur.execute(nuevo_sql)
        cur.execute("INSERT INTO pedidos_nueva SELECT * FROM pedidos")  # mismas columnas, mismo orden
        cur.execute("DROP TABLE pedidos")
        cur.execute("ALTER TABLE pedidos_nueva RENAME TO pedidos")
        cur.execute("COMMIT")
    except Exception:
        cur.execute("ROLLBACK")
        print("Algo falló: no se aplicó ningún cambio.")
        raise
    finally:
        con.execute("PRAGMA foreign_keys = ON")

    print("Pedidos:", con.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0], "filas conservadas.")
    print("Problemas de claves foráneas:", con.execute("PRAGMA foreign_key_check").fetchall())
    con.close()


if __name__ == "__main__":
    migrar()
