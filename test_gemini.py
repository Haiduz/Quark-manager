# test_gemini.py
from services import gemini_service
import json

def ejecutar_prueba():
    print("🚀 INICIANDO PRUEBA DE GEMINI...\n")
    
    mensaje_1 = "Anotame que tengo que pasar cotización de lecitina de Lasenor a la gente de Aceites del Valle para el jueves a la mañana."
    print(f"👤 Usuario (Turno 1): '{mensaje_1}'")
    print("🤖 Procesando...")
    
    # Recibimos el objeto chat activo
    datos_extraidos, chat_activo = gemini_service.extraer_datos_iniciales(mensaje_1, es_audio=False)
    
    print("\n✅ JSON RESULTANTE (Turno 1):")
    print(json.dumps(datos_extraidos, indent=2, ensure_ascii=False))
    
    print("\n" + "-"*50 + "\n")
    
    mensaje_2 = "Perdoná, me equivoqué de cliente. No era para Aceites del Valle, era para la cooperativa ACA. Lo demás dejalo igual."
    print(f"👤 Usuario (Corrección): '{mensaje_2}'")
    print("🤖 Reprocesando con el contexto anterior...")
    
    # Pasamos el objeto chat activo para que mantenga la memoria
    datos_corregidos, chat_activo = gemini_service.procesar_correccion(
        chat_existente=chat_activo, 
        texto_o_ruta_audio=mensaje_2, 
        es_audio=False
    )
    
    print("\n✅ JSON RESULTANTE (Turno 2 - Corregido):")
    print(json.dumps(datos_corregidos, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    ejecutar_prueba()