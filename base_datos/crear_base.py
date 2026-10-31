import sqlite3
from pathlib import Path

# La base se guarda al lado de este archivo, sin importar desde dónde lo ejecutes
RUTA_DB = Path(__file__).parent / "distribuidora.db"


def conectar():
    conexion = sqlite3.connect(RUTA_DB)
    # SQLite no controla las claves foráneas si no se lo pedimos
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


TABLAS = [
    """
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        razon_social TEXT NOT NULL,
        cuit TEXT NOT NULL UNIQUE,
        direccion_entrega TEXT,
        limite_credito REAL NOT NULL DEFAULT 0 CHECK (limite_credito >= 0),
        saldo_actual REAL NOT NULL DEFAULT 0,
        estado TEXT NOT NULL DEFAULT 'ACTIVO'
            CHECK (estado IN ('ACTIVO', 'BLOQUEADO_POR_DEUDA'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT NOT NULL UNIQUE,
        clave_hash TEXT NOT NULL,
        rol TEXT NOT NULL CHECK (rol IN ('admin', 'cliente')),
        cliente_id INTEGER,
        FOREIGN KEY (cliente_id) REFERENCES clientes (id),
        CHECK (rol = 'admin' OR cliente_id IS NOT NULL)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT NOT NULL UNIQUE,
        nombre TEXT NOT NULL,
        precio REAL NOT NULL CHECK (precio > 0),
        stock_fisico INTEGER NOT NULL DEFAULT 0 CHECK (stock_fisico >= 0),
        stock_reservado INTEGER NOT NULL DEFAULT 0 CHECK (stock_reservado >= 0),
        peso_kg REAL CHECK (peso_kg IS NULL OR peso_kg > 0),
        volumen_dm3 REAL CHECK (volumen_dm3 IS NULL OR volumen_dm3 > 0),
        imagen_url TEXT,
        activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
        CHECK (stock_reservado <= stock_fisico)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS precios_historial (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER NOT NULL,
        precio_anterior REAL NOT NULL CHECK (precio_anterior > 0),
        precio_nuevo REAL NOT NULL CHECK (precio_nuevo > 0),
        motivo TEXT,
        origen TEXT NOT NULL CHECK (origen IN ('ERP', 'AGENTE')),
        fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (producto_id) REFERENCES productos (id)
    )
    """,
]


def crear_tablas():
    conexion = conectar()
    for sentencia in TABLAS:
        conexion.execute(sentencia)
    conexion.commit()
    conexion.close()
    print("Tablas creadas (o ya existían).")


if __name__ == "__main__":
    crear_tablas()