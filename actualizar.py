import os
import json
import urllib.request
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def consultar_api(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode('utf-8'))

def obtener_serie_bcch(codigo_serie, user, token):
    hoy = datetime.now()
    hace_un_ano = hoy - timedelta(days=365)
    f_ini = hace_un_ano.strftime('%Y-%m-%d')
    f_fin = hoy.strftime('%Y-%m-%d')
    
    # Intento 1: URL directa sin codificar los símbolos '$'
    url_raw = f"https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx?user={user}&pass={token}&firstdate={f_ini}&lastdate={f_fin}&timeseries={codigo_serie}&function=GetSeries"
    
    try:
        data = consultar_api(url_raw)
        
        # Si da error -5, probamos codificando los símbolos '$' como '%24'
        if data.get('Codigo') == -5:
            token_encoded = token.replace('$', '%24')
            url_enc = f"https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx?user={user}&pass={token_encoded}&firstdate={f_ini}&lastdate={f_fin}&timeseries={codigo_serie}&function=GetSeries"
            data = consultar_api(url_enc)

        if data.get('Codigo') != 0:
            print(f"❌ [{codigo_serie}] Rechazo del BCCh -> Código {data.get('Codigo')}: {data.get('Descripcion')}")
            return None
            
        observaciones = data.get('Series', {}).get('Obs', [])
        
        # Recorremos de atrás hacia adelante buscando el último dato válido (ignorando 'NaN')
        for obs in reversed(observaciones):
            val = obs.get('value')
            if val is not None and val != 'NaN' and obs.get('statusCode') == 'OK':
                valor_limpio = float(val)
                print(f"✅ [{codigo_serie}] Dato obtenido: {valor_limpio} (Fecha: {obs.get('indexDateString')})")
                return valor_limpio
                
        print(f"⚠️ [{codigo_serie}] Serie recibida, pero sin observaciones numéricas válidas.")
    except Exception as e:
        print(f"🚨 Error técnico en {codigo_serie}: {e}")
    return None

def obtener_datos():
    bcch_user = os.getenv("BCCH_USER", "").strip()
    bcch_token = os.getenv("BCCH_TOKEN", "").strip()

    print(f"--- Diagnóstico de Credenciales ---")
    print(f"Largo del usuario: {len(bcch_user)} caracteres")
    print(f"Largo de la clave/token: {len(bcch_token)} caracteres")
    print(f"-----------------------------------")

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
    
    uf_str = f"${val_uf:,.0f}".replace(",", ".") if val_uf is not None else "N/D"
    dolar_str = f"${val_dolar:,.2f}".replace(",", ".") if val_dolar is not None else "N/D"
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
