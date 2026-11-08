# DistriApp · Sistema Multiagente de Distribución

Este proyecto automatiza el ciclo de ventas de una distribuidora de limpieza mediante un sistema multiagente construido sobre Paseo, OpenCode y FastAPI.

## 🛠️ Requisitos previos
- Python 3.10+
- Node.js (v18+)
- Uvicorn (`pip install uvicorn`)
- Paseo (instalado y con OpenCode configurado)

## 🚀 Cómo levantar el proyecto

### 1. Base de Datos

Abrí una terminal en la raíz del proyecto y ejecutá:
```bash
cd base_datos
python crear_base.py
python cargar_camiones.py
python crear_agentes_paseo.py
```

(Esto va a crear la base de datos distribuidora.db y las identidades de los 13 agentes).


### 2. API (Backend)

En la misma terminal:
cd ../api
pip install -r requirements.txt  # Si no tenés requirements, instalá: fastapi uvicorn pandas reportlab bcrypt pyjwt
uvicorn main:app --reload --port 8001

(La API va a correr en http://127.0.0.1:8001/docs).

### 3. Frontend (Opcional, para ver la tienda)

Abrí otra terminal:
cd frontend
npm install
npm run dev

(La tienda va a correr en http://localhost:5173).

### 4. Ejecutar el Harness (Agentes)

1. Abrí Paseo y cargá la carpeta del proyecto.

2. En el chat del agente, pegá este prompt para hacer el test de humo:

"Hola. Leé el archivo agentes/supervisor.md y el playbook.md. Verificá que la API esté corriendo y decime cuántos pedidos hay en estado RECIBIDO."

### 5. Verificar el sistema (Test de integración)

Para asegurarte de que la API, el stock y la base de datos funcionan correctamente, ejecutá en la raíz:
python check.py

Si todo está bien, verás: TODOS LOS CHEQUEOS PASARON. EL HARNESS ESTA LISTO.
