import subprocess
import sys

def run_check():
    print("🔍 INICIANDO CHEQUEO DEL HARNESS...\n")
    
    # 1. Correr el test de integración
    print("▶️  Ejecutando test de integración (API)...")
    result_test = subprocess.run(["python", "tests/test_flujo_completo.py"])
    
    if result_test.returncode != 0:
        print("\n❌ ERROR: El test de integración falló.")
        sys.exit(1)
        
    print("\n✅ Test de integración pasado.\n")
    
    # 2. Probar el validador de salida (con un ejemplo)
    print("▶️  Ejecutando validador de salida (formato)...")
    result_val = subprocess.run([
        "python", "agentes/validar_salida.py", 
        "VEREDICTO: ✅ APROBADO\nPEDIDOS_VALIDADOS: [1, 2, 3]\nTOTAL: 3", 
        "recepcionista"
    ])
    
    if result_val.returncode != 0:
        print("\n❌ ERROR: El validador de salida falló.")
        sys.exit(1)
        
    print("\n✅ Validador de salida pasado.")
    print("\n🎉 TODOS LOS CHEQUEOS PASARON. EL HARNESS ESTÁ LISTO.\n")

if __name__ == "__main__":
    run_check()