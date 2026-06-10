# services/sheets_service.py
from datetime import datetime

# Cuando conectemos la API de Google, importaremos gspread aquí.

async def actualizar_status_cliente(empresa: str, cliente_oficial: str, nueva_accion: str, fecha_formato: str) -> bool:
    """
    Esta función buscará al cliente en la pestaña correspondiente de Google Sheets 
    y agregará la nueva acción al principio de la celda de 'Status y comentarios'.
    """
    print("\n" + "="*50)
    print("🔌 [MOCK] CONECTANDO CON GOOGLE SHEETS API...")
    
    # Lógica que usaremos con gspread:
    # 1. if empresa == "KEMIN": sheet = documento.worksheet("KEMIN Clientes")
    # 2. cell = sheet.find(cliente_oficial)
    # 3. texto_viejo = sheet.cell(cell.row, columna_status).value
    
    # Simulamos el texto viejo que habría en la celda
    texto_viejo = "15/05/26: Se le enviaron muestras de producto."
    
    # Armamos la nueva estampa de tiempo
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")
    
    # Concatenamos la novedad arriba de lo viejo
    texto_actualizado = f"[{fecha_hoy}] Recordatorio ({fecha_formato}): {nueva_accion}\n{texto_viejo}"
    
    print(f"📊 PLANILLA SELECCIONADA: {empresa}")
    print(f"🔎 BUSCANDO FILA DE: {cliente_oficial}")
    print(f"📝 ESCRIBIENDO NUEVO STATUS:\n{texto_actualizado}")
    print("="*50 + "\n")
    
    # 4. sheet.update_cell(cell.row, columna_status, texto_actualizado)
    
    return True