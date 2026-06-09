# services/telegram_service.py
import os
import json
import httpx

# Cargamos el Token desde el entorno (asegúrate de que main.py ejecutó load_dotenv() primero)
TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

async def enviar_mensaje_simple(chat_id: int, texto: str):
    """Envía un texto plano con formato Markdown"""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

async def enviar_resumen_con_botones(chat_id: int, datos: dict):
    """Envía el resumen estructurado acompañado de los 3 botones físicos"""
    url = f"{TELEGRAM_API_URL}/sendMessage"
    
    resumen = (
        f"📝 *¿La información es correcta?*\n\n"
        f"• *Cliente:* {datos['entidad']}\n"
        f"• *Contacto:* {datos['destinatario']}\n"
        f"• *Fecha:* {datos['fecha']}\n"
        f"• *Acción:* {datos['accion']}\n\n"
        f"ℹ️ _Estado actual: {datos['origen']}_"
    )
    
    teclado = {
        "inline_keyboard": [
            [
                {"text": "✅ Sí, guardar", "callback_data": "confirmar_si"},
                {"text": "❌ No, cancelar", "callback_data": "confirmar_no"}
            ],
            [
                {"text": "✏️ Editar recordatorio", "callback_data": "confirmar_editar"}
            ]
        ]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": resumen,
        "parse_mode": "Markdown",
        "reply_markup": json.dumps(teclado)
    }
    
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

async def descargar_audio(file_id: int) -> str:
    """
    Toma el file_id del mensaje de voz de Telegram y descarga el archivo .ogg a la computadora.
    Devuelve la ruta (path) donde se guardó el archivo.
    """
    async with httpx.AsyncClient() as client:
        # 1. Le preguntamos a Telegram la ruta del archivo
        url_get_file = f"{TELEGRAM_API_URL}/getFile?file_id={file_id}"
        respuesta_file = await client.get(url_get_file)
        datos_file = respuesta_file.json()
        
        if not datos_file.get("ok"):
            print("❌ Error al obtener la ruta del archivo de Telegram.")
            return ""
            
        file_path = datos_file["result"]["file_path"]
        
        # 2. Descargamos el archivo real de los servidores de Telegram
        url_descarga = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
        respuesta_descarga = await client.get(url_descarga)
        
        # 3. Lo guardamos en una carpeta temporal (asegurate de crearla o guardalo en raíz por ahora)
        nombre_archivo = "audio_temporal.ogg"
        with open(nombre_archivo, 'wb') as f:
            f.write(respuesta_descarga.content)
            
        print(f"✅ Audio descargado exitosamente como: {nombre_archivo}")
        return nombre_archivo
    
async def responder_callback(callback_id: str, texto_alerta: str = ""):
    """Detiene la animación de carga del botón en Telegram. 
    Opcionalmente puede mostrar un cartelito pop-up."""
    url = f"{TELEGRAM_API_URL}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id}
    
    if texto_alerta:
        payload["text"] = texto_alerta
        
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)

async def quitar_botones(chat_id: int, message_id: int):
    """Edita el mensaje original para borrarle los botones y que no se puedan volver a apretar."""
    url = f"{TELEGRAM_API_URL}/editMessageReplyMarkup"
    # Le mandamos un teclado vacío para pisar el anterior
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "reply_markup": json.dumps({"inline_keyboard": []}) 
    }
    async with httpx.AsyncClient() as client:
        await client.post(url, json=payload)