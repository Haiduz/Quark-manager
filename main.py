import os
import json
from fastapi import FastAPI, Request
from dotenv import load_dotenv
import httpx

# 1. CONFIGURACIÓN E INICIALIZACIÓN
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

app = FastAPI(title="Copiloto de Ventas Quark - Mock Environment")

# Memoria temporal de estados (State Machine)
# Mañana esto mantendrá el "ChatSession" real de la API de Gemini
MEMORIA_ESTADOS = {}

# 2. FUNCIONES AUXILIARES (COMUNICACIÓN CON TELEGRAM)
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
        f"ℹ️ _Estado actual del Servidor: {datos['origen']}_"
    )
    
    # Construcción del teclado interactivo (Inline Keyboard)
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

# 3. ENDPOINT PRINCIPAL (EL WEBHOOK)
@app.post("/webhook")
async def recibir_webhook(request: Request):
    datos_telegram = await request.json()
    
    # -----------------------------------------------------------------
    # CONTROLADOR A: SE INTERCEPTA EL CLIC DE UN BOTÓN (Callback Query)
    # -----------------------------------------------------------------
    if "callback_query" in datos_telegram:
        callback = datos_telegram["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        accion_boton = callback["data"] 
        
        if chat_id not in MEMORIA_ESTADOS:
            return {"estado": "ok"}
            
        usuario = MEMORIA_ESTADOS[chat_id]
        
        if accion_boton == "confirmar_si":
            datos = usuario["datos_pendientes"]
            await enviar_mensaje_simple(
                chat_id, 
                f"🚀 *[MOCK] ¡Acción Confirmada!*\n"
                f"El backend enviaría ahora estos datos a Google Sheets usando `gspread`:\n"
                f"• Row: `{datos['entidad']} | {datos['destinatario']} | {datos['accion']}`\n\n"
                f"🤖 *Bot:* Volviendo a estado libre (IDLE)."
            )
            # Reseteamos estado del usuario
            usuario["estado"] = "IDLE"
            usuario["datos_pendientes"] = None
            
        elif accion_boton == "confirmar_no":
            await enviar_mensaje_simple(chat_id, "❌ *Operación Cancelada.*\nSe eliminaron los datos temporales de la memoria. Estoy listo para un nuevo recordatorio.")
            usuario["estado"] = "IDLE"
            usuario["datos_pendientes"] = None
            
        elif accion_boton == "confirmar_editar":
            usuario["estado"] = "AWAITING_EDIT"
            await enviar_mensaje_simple(
                chat_id, 
                "✏️ *Modo Edición Activado.*\n"
                "Envíame la corrección por *audio o texto*.\n"
                "_(Ejemplo: 'No, acordate que era para el jueves' o 'Cambiá el cliente a ACA')_"
            )

        return {"estado": "ok"}

    # -----------------------------------------------------------------
    # CONTROLADOR B: SE INTERCEPTA UN MENSAJE ENTRANTE (Texto o Voz)
    # -----------------------------------------------------------------
    if "message" in datos_telegram:
        mensaje = datos_telegram["message"]
        chat_id = mensaje["chat"]["id"]
        
        # Inicialización del usuario en nuestra máquina de estados
        if chat_id not in MEMORIA_ESTADOS:
            MEMORIA_ESTADOS[chat_id] = {"estado": "IDLE", "datos_pendientes": None}
            
        usuario = MEMORIA_ESTADOS[chat_id]
        
        # Normalización del input del usuario
        texto_recibido = ""
        if "voice" in mensaje:
            texto_recibido = "[Mensaje de Voz Recibido]"
            print(f"🎤 Audio detectado en consola. ID: {mensaje['voice']['file_id']}")
        elif "text" in mensaje:
            texto_recibido = mensaje["text"].strip()
            print(f"💬 Texto detectado en consola: {texto_recibido}")

        # FLUJO 1: El usuario estaba en modo edición y mandó una corrección
        if usuario["estado"] == "AWAITING_EDIT":
            await enviar_mensaje_simple(chat_id, f"🔄 *[MOCK IA]* Reprocesando historial de chat incluyendo tu cambio: _'{texto_recibido}'_...")
            
            # Simulamos que la IA entendió la corrección y modificó el JSON previo
            datos_corregidos = {
                "entidad": "ACA coop Agrarias Argentinas",
                "destinatario": "Administración Quark",
                "fecha": "11/06/2026", # Simulamos que corrigió la fecha al jueves
                "accion": "Reunión urgente por stock de Antioxidantes (Kemin)",
                "origen": "Simulación de Segunda Vuelta (IA Corregida)"
            }
            usuario["datos_pendientes"] = datos_corregidos
            # Volvemos a mostrar el componente visual con los botones
            await enviar_resumen_con_botones(chat_id, datos_corregidos)
            
        # FLUJO 2: El bot estaba libre (IDLE) y recibe una orden desde cero
        elif usuario["estado"] == "IDLE":
            if texto_recibido == "/start":
                await enviar_mensaje_simple(
                    chat_id, 
                    "🚀 *¡Bienvenido al Backend de Copiloto Quark!*\n\n"
                    "Este es un entorno de prueba local. Mándame un mensaje o un audio simulando una gestión de ventas."
                )
            else:
                # Simulamos la primera respuesta que nos daría Gemini estructurada
                datos_iniciales = {
                    "entidad": "Aceites del Valle",
                    "destinatario": "Lara Zuchini",
                    "fecha": "12/06/2026",
                    "accion": "Pasar cotización actualizada de Lecitina (Lasenor)",
                    "origen": "Simulación de Primera Vuelta (IA Inicial)"
                }
                usuario["datos_pendientes"] = datos_iniciales
                # Bloqueamos al usuario en estado de confirmación hasta que toque un botón
                usuario["estado"] = "IDLE" # Permitimos que vuelva a disparar para probar libremente
                
                await enviar_resumen_con_botones(chat_id, datos_iniciales)

    return {"estado": "ok"}