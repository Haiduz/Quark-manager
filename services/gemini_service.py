# services/gemini_service.py
import os
import json
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=GEMINI_API_KEY)

def obtener_configuracion_dinamica():
    """
    Genera el System Prompt calculando la fecha exacta de hoy.
    De esta forma, la IA siempre sabe en qué día vive y puede calcular relativos (mañana, el jueves, etc).
    """
    # Calculamos la fecha actual al momento exacto de recibir el mensaje
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    
    instruccion_sistema = f"""
    Eres un asistente experto en extracción de datos para un agente comercial independiente.
    Tu único trabajo es recibir audios o textos de tu jefe y extraer entidades clave de forma estructurada.
    
    CONTEXTO TEMPORAL CRÍTICO:
    Hoy es {fecha_hoy}. Usa esta fecha absoluta como base para calcular cualquier día relativo que mencione el usuario (ej: "mañana", "el jueves", "la semana que viene").
    
    REGLAS ESTRICTAS:
    1. NUNCA inventes información. Si un dato no se menciona, pon "No especificado".
    2. FORMATO DE FECHA: Transforma SIEMPRE la fecha resultante al formato numérico continuo DDMMAA (Día, Mes, Año en 2 dígitos).
       - Ejemplo: si hoy es 2026-06-09 y piden "para el jueves", el jueves es 11 de junio, devuelves "110626".
       - Ejemplo: si piden "mañana", devuelves "100626".
    3. DEBES devolver ÚNICAMENTE un objeto JSON válido, sin formato Markdown ni texto adicional.

    ESTRUCTURA JSON REQUERIDA:
    {{
      "entidad": "Nombre de la empresa o cliente",
      "destinatario": "Nombre de la persona de contacto",
      "fecha": "Formato estricto DDMMAA. Si el usuario no menciona ninguna fecha, pon 'No especificado'",
      "accion": "Descripción breve y ejecutiva de lo que hay que hacer o recordar"
    }}
    """
    
    return types.GenerateContentConfig(
        system_instruction=instruccion_sistema,
        temperature=0.0
    )

def extraer_datos_iniciales(texto_o_ruta_audio: str, es_audio: bool = False):
    # Generamos la configuración inyectando el tiempo actual en este preciso instante
    configuracion = obtener_configuracion_dinamica()
    chat = client.chats.create(model="gemini-2.5-flash", config=configuracion)
    
    if es_audio:
        print("🧠 Subiendo audio crudo a Gemini...")
        archivo = client.files.upload(file=texto_o_ruta_audio)
        respuesta = chat.send_message(["Extrae los datos de este audio comercial.", archivo])
    else:
        respuesta = chat.send_message(f"Extrae los datos de este texto comercial: {texto_o_ruta_audio}")
        
    texto_limpio = respuesta.text.replace("```json", "").replace("```", "").strip()
    
    try:
        datos_json = json.loads(texto_limpio)
        return datos_json, chat
    except json.JSONDecodeError:
        print("❌ Gemini no devolvió un JSON válido:", respuesta.text)
        return {}, chat

def procesar_correccion(chat_existente, texto_o_ruta_audio: str, es_audio: bool = False):
    # Nota: No hace falta inyectar la fecha aquí, el chat_existente ya tiene la memoria de hoy.
    if es_audio:
        archivo = client.files.upload(file=texto_o_ruta_audio)
        respuesta = chat_existente.send_message(["Aplica esta corrección al recordatorio anterior y devuelve el JSON completo actualizado.", archivo])
    else:
        respuesta = chat_existente.send_message(f"Aplica esta corrección al recordatorio anterior: '{texto_o_ruta_audio}'. Devuelve el JSON completo actualizado.")
        
    texto_limpio = respuesta.text.replace("```json", "").replace("```", "").strip()
    
    try:
        datos_json = json.loads(texto_limpio)
        return datos_json, chat_existente
    except json.JSONDecodeError:
        print("❌ Gemini no devolvió un JSON válido en la corrección:", respuesta.text)
        return {}, chat_existente