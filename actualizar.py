import os
import json
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def obtener_serie_bcch(codigo_serie, user, token):
    """Función para consultar la API del Banco Central filtrando solo el último año"""
    url = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
    
    hoy = datetime.now()
    hace_un_ano = hoy - timedelta(days=365)
    
    parametros = {
        "user": user,
        "pass": token,
        "firstdate": hace_un_ano.strftime("%Y-%m-%d"),
        "lastdate": hoy.strftime("%Y-%m-%d"),
        "timeseries": codigo_serie,
        "function": "GetSeries"
    }
    
    try:
        resp = requests.get(url, params=parametros, timeout=15)
        data = resp.json()
        
        # LÍNEA NUEVA: Imprimimos la respuesta exacta del Banco Central para depurar
        print(f"Respuesta {codigo_serie}: {data}")
        
        if 'CodigoError' in data and data['CodigoError'] != 0:
            print(f"Error de API para {codigo_serie}: {data.get('DescripcionError')}")
            return None
            
        observaciones = data.get('Series', {}).get('Obs', [])
        if observaciones:
            return float(observaciones[-1].get('value', 0))
    except Exception as e:
        print(f"Error de conexión en {codigo_serie}: {e}")
    return None

def obtener_datos():
    bcch_user = os.getenv("BCCH_USER")
    bcch_token = os.getenv("BCCH_TOKEN")

    # LÍNEAS NUEVAS PARA DEPURACIÓN
    print(f"¿Usuario cargado?: {bool(bcch_user)}")
    print(f"¿Token cargado?: {bool(bcch_token)}")

    codigos = {
        "uf": "F073.UFF.PRE.Z.D",
        "dolar": "F073.TCO.PRE.Z.D",
        "tpm": "F073.TPM.TIN.Z.D",
        "ipc_mensual": "F073.IPC.VAR.Z.Z.C.M",
        "inflacion_anual": "F073.IPC.V12.Z.Z.C.M"
    }

    val_uf = obtener_serie_bcch(codigos["uf"], bcch_user, bcch_token)
    val_dolar = obtener_serie_bcch(codigos["dolar"], bcch_user, bcch_token)
    val_tpm = obtener_serie_bcch(codigos["tpm"], bcch_user, bcch_token)
    val_ipc = obtener_serie_bcch(codigos["ipc_mensual"], bcch_user, bcch_token)
    val_inflacion = obtener_serie_bcch(codigos["inflacion_anual"], bcch_user, bcch_token)
    
    uf_str = f"${val_uf:,.0f}".replace(",", ".") if val_uf else "N/D"
    dolar_str = f"${val_dolar:,.2f}".replace(",", ".") if val_dolar else "N/D"
    tpm_str = f"{val_tpm}%" if val_tpm is not None else "N/D"
    ipc_str = f"{val_ipc}%" if val_ipc is not None else "N/D"
    inflacion_str = f"{val_inflacion}%" if val_inflacion is not None else "N/D"
    pib_usd_str = "335.000 Millones USD" 

    try:
        resp_min = requests.get("https://mindicador.cl/api", timeout=10).json()
        desempleo_num = resp_min.get("tasa_desempleo", {}).get("valor", None)
        desempleo_str = f"{desempleo_num}%" if desempleo_num else "N/D"
    except:
        desempleo_str = "N/D"

    hora_chile = datetime.now(ZoneInfo("America/Santiago"))

    indicadores = {
        "actualizado": hora_chile.strftime("%d-%m-%Y %H:%M"),
        "uf": uf_str,
        "dolar": dolar_str,
        "tpm": tpm_str,
        "ipc": ipc_str,
        "inflacion_total": inflacion_str,
        "desempleo": desempleo_str,
        "pib_usd": pib_usd_str
    }

    with open("indicadores.json", "w", encoding="utf-8") as f:
        json.dump(indicadores, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    obtener_datos()
