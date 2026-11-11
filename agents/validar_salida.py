"""
Sensor de validación de salida.
Verifica que el texto devuelto por un agente cumpla con el formato esperado.
Uso: python agents/validar_salida.py "<texto_del_agente>" "<tipo_de_agente>"
"""

import re
import sys
import json

# Formatos esperados por tipo de agente (acepta con o sin emojis)
FORMATOS = {
    "recepcionista": {
        "veredicto": r"VEREDICTO:\s*(?:✅\s*)?(APROBADO|❌\s*EXCEPCION)",
        "campos": ["PEDIDOS_VALIDADOS", "TOTAL"],
    },
    "validador_precios": {
        "veredicto": r"VEREDICTO:\s*(?:✅\s*)?(APROBADO|❌\s*EXCEPCION)",
        "campos": ["OBSERVACIONES"],
    },
    "validador_credito": {
        "veredicto": r"VEREDICTO:\s*(?:✅\s*)?(APROBADO|❌\s*EXCEPCION)",
        "campos": ["OBSERVACIONES"],
    },
    "preparador": {
        "veredicto": r"VEREDICTO:\s*(?:✅\s*)?(APROBADO)",
        "campos": ["PEDIDOS_PREPARADOS"],
    },
    "facturador": {
        "veredicto": r"VEREDICTO:\s*(?:✅\s*)?(APROBADO)",
        "campos": ["FACTURAS_EMITIDAS"],
    },
    "planificador": {
        "veredicto": r"VEREDICTO:\s*(?:✅\s*)?(APROBADO)",
        "campos": ["PEDIDOS_EN_RUTA", "CAMION"],
    },
    "auditor": {
        "veredicto": r"VEREDICTO:\s*(?:✅\s*)?(APROBADO|⚠️\s*APROBADO CON OBSERVACIONES|❌\s*RECHAZADO)",
        "campos": ["CHEQUEOS", "OBSERVACIONES"],
    },
    "registro": {
        "veredicto": r"VEREDICTO:\s*(?:✅\s*)?(APROBADO)",
        "campos": ["EVENTO_ID"],
    },
    "gestor_precios": {
        "veredicto": r"VEREDICTO:\s*(?:✅\s*)?(APROBADO)",
        "campos": ["PRODUCTOS_ACTUALIZADOS"],
    },
    "reposicion": {
        "veredicto": r"VEREDICTO:\s*(?:✅\s*)?(APROBADO)",
        "campos": ["ALERTAS_RESUELTAS", "MENSAJE"],
    },
    "simulador_humano": {
        "veredicto": r"VEREDICTO:\s*(?:✅\s*)?(APROBADO)",
        "campos": ["PEDIDOS_ARMADOS", "PEDIDOS_ENTREGADOS"],
    },
}

def validar(texto: str, tipo_agente: str) -> dict:
    if tipo_agente not in FORMATOS:
        return {
            "valido": False,
            "error": f"Tipo de agente desconocido: {tipo_agente}",
            "formatos_validos": list(FORMATOS.keys()),
        }

    formato = FORMATOS[tipo_agente]
    resultado = {"valido": True, "agente": tipo_agente, "errores": []}

    # 1. Verificar veredicto
    match_veredicto = re.search(formato["veredicto"], texto)
    if not match_veredicto:
        resultado["valido"] = False
        resultado["errores"].append(
            f"Falta VEREDICTO válido. Esperado: {formato['veredicto']}"
        )
    else:
        resultado["veredicto"] = match_veredicto.group(1)

    # 2. Verificar campos obligatorios
    for campo in formato["campos"]:
        if campo not in texto:
            resultado["valido"] = False
            resultado["errores"].append(f"Falta el campo obligatorio: {campo}")

    # 3. Verificar que los IDs sean números enteros
    if re.search(r"PEDIDOS_\w+:\s*\[([^\]]*)\]", texto):
        ids_str = re.search(r"PEDIDOS_\w+:\s*\[([^\]]*)\]", texto).group(1)
        if ids_str.strip():
            ids = [x.strip() for x in ids_str.split(",") if x.strip()]
            for id_str in ids:
                if not id_str.isdigit():
                    resultado["valido"] = False
                    resultado["errores"].append(
                        f"ID no numérico detectado: {id_str}"
                    )

    return resultado

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python agents/validar_salida.py \"<texto>\" \"<tipo_agente>\"")
        print("Tipos válidos:", ", ".join(FORMATOS.keys()))
        sys.exit(1)

    texto = sys.argv[1]
    tipo = sys.argv[2]
    resultado = validar(texto, tipo)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    sys.exit(0 if resultado["valido"] else 1)