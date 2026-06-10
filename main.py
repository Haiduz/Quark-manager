# main.py
import os
import asyncio
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from services import telegram_services, gemini_service, matcher_service, sheets_service

load_dotenv()

# Importamos ambos servicios modulares
from services import telegram_services, gemini_service

app = FastAPI(title="Copiloto de Ventas Quark")

MEMORIA_ESTADOS = {}

@app.post("/webhook")
async def recibir_webhook(request: Request):
    datos_telegram = await request.json()
    
    # -----------------------------------------------------------------
    # CONTROLADOR A: CLIC DE UN BOTÓN (Callback Query)
    # -----------------------------------------------------------------
    if "callback_query" in datos_telegram:
        callback = datos_telegram["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"] 
        callback_id = callback["id"] 
        accion_boton = callback["data"] 
        
        if chat_id not in MEMORIA_ESTADOS: 
            await telegram_services.responder_callback(callback_id, "⏳ Sesión expirada.")
            return {"estado": "ok"}
            
        usuario = MEMORIA_ESTADOS[chat_id]
        
        if usuario["estado"] not in ["AWAITING_CONFIRMATION", "AWAITING_EDIT"]:
            await telegram_services.responder_callback(callback_id, "⚠️ Esta acción ya fue procesada.")
            return {"estado": "ok"}

        await telegram_services.responder_callback(callback_id)
        await telegram_services.quitar_botones(chat_id, message_id)
        
        if accion_boton == "confirmar_si":
            datos = usuario["datos_pendientes"]
            
            # Avisamos que estamos guardando
            await telegram_services.responder_callback(callback_id, "Guardando en Google Sheets...")
            await telegram_services.quitar_botones(chat_id, message_id)
            
            # Si el cliente fue encontrado, llamamos al archivista
            if datos.get("empresa") != "DESCONOCIDA":
                exito = await sheets_service.actualizar_status_cliente(
                    empresa=datos["empresa"],
                    cliente_oficial=datos["entidad"],
                    nueva_accion=datos["accion"],
                    fecha_formato=datos["fecha"]
                )
                await telegram_services.enviar_mensaje_simple(chat_id, f"✅ *¡Guardado exitosamente!*\nSe actualizó la columna Status de *{datos['entidad']}* en la planilla de _{datos['empresa']}_.")
            else:
                await telegram_services.enviar_mensaje_simple(chat_id, f"⚠️ *Atención:* El recordatorio fue procesado, pero no se guardó en Google Sheets porque el cliente no existe en KEMIN ni CORLASA.")
            
            usuario["estado"] = "IDLE"
            usuario["datos_pendientes"] = None
            usuario["chat_ia"] = None
            
        elif accion_boton == "confirmar_no":
            await telegram_services.enviar_mensaje_simple(chat_id, "❌ *Operación Cancelada.*")
            usuario["estado"] = "IDLE"
            usuario["datos_pendientes"] = None
            usuario["chat_ia"] = None
            
        elif accion_boton == "confirmar_editar":
            usuario["estado"] = "AWAITING_EDIT"
            await telegram_services.enviar_mensaje_simple(chat_id, "✏️ *Modo Edición.* Envíame la corrección por audio o texto.")

        return {"estado": "ok"}

    # -----------------------------------------------------------------
    # CONTROLADOR B: MENSAJE ENTRANTE (Texto o Voz)
    # -----------------------------------------------------------------
    if "message" in datos_telegram:
        mensaje = datos_telegram["message"]
        chat_id = mensaje["chat"]["id"]
        
        # Agregamos la clave "chat_ia" a la memoria para guardar la sesión de Gemini
        if chat_id not in MEMORIA_ESTADOS:
            MEMORIA_ESTADOS[chat_id] = {"estado": "IDLE", "datos_pendientes": None, "chat_ia": None}
            
        usuario = MEMORIA_ESTADOS[chat_id]
        texto_recibido = ""
        ruta_audio = ""
        es_mensaje_audio = False
        
        # --- CAPTURA DEL INPUT ---
        if "voice" in mensaje:
            es_mensaje_audio = True
            file_id = mensaje["voice"]["file_id"]
            ruta_audio = await telegram_services.descargar_audio(file_id)
        elif "text" in mensaje:
            texto_recibido = mensaje["text"].strip()

        # --- FLUJO 1: APLICAR CORRECCIÓN ---
        if usuario["estado"] == "AWAITING_EDIT":
            await telegram_services.enviar_mensaje_simple(chat_id, "🔄 _Aplicando corrección con IA..._")
            
            chat_activo = usuario["chat_ia"]
            
            # Usamos asyncio.to_thread para que la llamada a la API de Google no bloquee el servidor
            if es_mensaje_audio:
                datos_corregidos, chat_actualizado = await asyncio.to_thread(
                    gemini_service.procesar_correccion, chat_activo, ruta_audio, True
                )
            else:
                datos_corregidos, chat_actualizado = await asyncio.to_thread(
                    gemini_service.procesar_correccion, chat_activo, texto_recibido, False
                )
            
            datos_corregidos["origen"] = "Gemini Flash (Corregido)"

            # ¡ACÁ CORREGIMOS EL BUG! Usamos datos_corregidos en lugar de datos_iniciales
            resultado_match = matcher_service.cruzar_con_cartera(datos_corregidos["entidad"])
            
            if resultado_match["encontrado"]:
                datos_corregidos["entidad"] = resultado_match["cliente_oficial"]
                datos_corregidos["empresa"] = resultado_match["empresa_representada"]
                datos_corregidos["origen"] += f"\n✅ Match: {resultado_match['empresa_representada']} ({resultado_match['porcentaje_confianza']}%)"
            else:
                datos_corregidos["origen"] += f"\n⚠️ No se encontró el cliente en la base de datos."
                datos_corregidos["empresa"] = "DESCONOCIDA"

            usuario["datos_pendientes"] = datos_corregidos
            usuario["chat_ia"] = chat_actualizado
            usuario["estado"] = "AWAITING_CONFIRMATION" 
            
            await telegram_services.enviar_resumen_con_botones(chat_id, datos_corregidos)
            
        # --- FLUJO 2: NUEVO RECORDATORIO ---
        elif usuario["estado"] == "IDLE":
            if texto_recibido == "/start":
                await telegram_services.enviar_mensaje_simple(chat_id, "🚀 ¡Cerebro conectado! Mándame un audio con tu gestión.")
            else:
                await telegram_services.enviar_mensaje_simple(chat_id, "⏳ _Escuchando y procesando..._")
                
                if es_mensaje_audio:
                    datos_iniciales, chat_nuevo = await asyncio.to_thread(
                        gemini_service.extraer_datos_iniciales, ruta_audio, True
                    )
                else:
                    datos_iniciales, chat_nuevo = await asyncio.to_thread(
                        gemini_service.extraer_datos_iniciales, texto_recibido, False
                    )
                
                datos_iniciales["origen"] = "Gemini Flash (Turno 1)"

                # ¡ACÁ OCURRE LA MAGIA DEL MATCHING!
                resultado_match = matcher_service.cruzar_con_cartera(datos_iniciales["entidad"])
                
                if resultado_match["encontrado"]:
                    # Pisamos el nombre que entendió la IA con el nombre oficial de la base de datos
                    datos_iniciales["entidad"] = resultado_match["cliente_oficial"]
                    datos_iniciales["empresa"] = resultado_match["empresa_representada"]
                    
                    # Le agregamos un cartelito al resumen para que el usuario vea la magia
                    datos_iniciales["origen"] += f"\n✅ Match: {resultado_match['empresa_representada']} ({resultado_match['porcentaje_confianza']}%)"
                else:
                    datos_iniciales["origen"] += f"\n⚠️ No se encontró el cliente en la base de datos."
                    datos_iniciales["empresa"] = "DESCONOCIDA"
                
                # Guardamos los datos y la memoria temporal del chat en nuestra máquina de estados
                usuario["datos_pendientes"] = datos_iniciales
                usuario["chat_ia"] = chat_nuevo
                usuario["estado"] = "AWAITING_CONFIRMATION" 
                
                await telegram_services.enviar_resumen_con_botones(chat_id, datos_iniciales)

    return {"estado": "ok"}