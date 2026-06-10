# services/matcher_service.py
from thefuzz import process

# MOCK DE BASE DE DATOS (Extraído exactamente de tus CSVs)
# Mañana, esta lista la llenará sheets_service.py leyendo Google Sheets en tiempo real
CLIENTES_DB = {
    "KEMIN": [
        "Aceites del Valle", "Aceitera Colibri", "Adama SA", "AdecoAgro", 
        "Renderest SAS", "RIS Bionutricion SA", "SL Natural", "Swift", 
        "Unilever", "Sanchez y Sannchez", "Santa Clara Alimentos"
    ],
    "CORLASA / CREMIGAL": [
        "ACA coop Agrarias Argetinas", "Alimentaria Montecristo SRL - OBLITAS", 
        "AlphaTrade SRL", "Biofarma", "Biotecnica Argentina SA", "Nutrifarms", 
        "Patagonia Grains", "Pastas La Morocha", "Producir SRL - Crespo -", 
        "PROVIMI", "Quesada Lacteos CEI SRL"
    ]
}

def cruzar_con_cartera(entidad_ia: str) -> dict:
    """
    Toma el nombre extraído por la IA y busca la coincidencia matemática más cercana
    en la cartera de clientes de todas las representaciones.
    """
    if entidad_ia == "No especificado":
        return {"encontrado": False, "motivo": "La IA no detectó un cliente en el audio."}

    todos_los_clientes = []
    mapa_empresas = {}
    
    # Unificamos a todos los clientes en una lista y recordamos de qué empresa son
    for empresa, clientes in CLIENTES_DB.items():
        for c in clientes:
            todos_los_clientes.append(c)
            mapa_empresas[c] = empresa
            
    # MATEMÁTICA PURA: Compara "entidad_ia" contra toda la lista
    # Retorna la mejor coincidencia y un puntaje de 0 a 100
    mejor_match, puntaje = process.extractOne(entidad_ia, todos_los_clientes)
    
    # Definimos un umbral de confianza (70% suele ser ideal para voces y errores de tipeo)
    if puntaje >= 70:
        empresa_origen = mapa_empresas[mejor_match]
        return {
            "encontrado": True,
            "cliente_oficial": mejor_match,
            "empresa_representada": empresa_origen,
            "porcentaje_confianza": puntaje
        }
    else:
        return {
            "encontrado": False,
            "motivo": f"Se entendió '{entidad_ia}' pero la coincidencia más cercana fue '{mejor_match}' con solo {puntaje}% de seguridad. Demasiado riesgo para guardar."
        }