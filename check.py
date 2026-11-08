import subprocess
import sys
import os
import io 

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def run_check():
    print("INICIANDO CHEQUEO DEL HARNESS...\n")
    
    # Configurar encoding para Windows
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    
    # 1. Correr el test de integración
    print("Ejecutando test de integracion (API)...")
    result_test = subprocess.run(["python", "tests/test_flujo_completo.py"], env=env)
    
    if result_test.returncode != 0:
        print("\nERROR: El test de integracion fallo.")
        sys.exit(1)
        
    print("\nTest de integracion pasado.\n")
    
    # 2. Probar el validador de salida
    print("Ejecutando validador de salida (formato)...")
    result_val = subprocess.run([
        "python", "agents/validar_salida.py", 
        "VEREDICTO: APROBADO\nPEDIDOS_VALIDADOS: [1, 2, 3]\nTOTAL: 3", 
        "recepcionista"
    ], env=env)
    
    if result_val.returncode != 0:
        print("\nERROR: El validador de salida fallo.")
        sys.exit(1)
        
    print("\nValidador de salida pasado.")
    print("\nTODOS LOS CHEQUEOS PASARON. EL HARNESS ESTA LISTO.\n")

if __name__ == "__main__":
    run_check()