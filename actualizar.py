from datetime import datetime
import json
import requests
from zoneinfo import ZoneInfo

def obtener_datos():
    # 1. Variables de mercado y corto plazo (mindicador)
    url_api = "https://mindicador.cl/api"
    resp = requests.get(url_api, timeout=10)
    data = resp.json()

    uf_val = f"${data['uf']['valor']:,.0f}".replace(",", ".")
    dolar_val = f"${data['dolar']['valor']:,.2f}".replace(",", ".")
    
    desempleo_num = data.get("tasa_desempleo", {}).get("valor", None)
    desempleo_val = f"{desempleo_num}%" if desempleo_num else "N/D"

    # 2. Variables macroestructurales
    # Al no variar diariamente, se definen como constantes en el widget 
    # hasta la próxima entrega de Cuentas Nacionales / IPC mensual del INE.
    inflacion_anual_val = "4,1%" 
    pib_usd_val = "335.000 Millones USD"

    hora_chile = datetime.now(ZoneInfo("America/Santiago"))

    indicadores = {
        "actualizado": hora_chile.strftime("%d-%m-%Y %H:%M"),
        "uf": uf_val,
        "dolar": dolar_val,
        "desempleo": desempleo_val,
        "inflacion_total": inflacion_anual_val,
        "pib_usd": pib_usd_val
    }

    with open("indicadores.json", "w", encoding="utf-8") as f:
        json.dump(indicadores, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    obtener_datos()
