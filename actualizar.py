import os
import json
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def consultar_serie_bcch(lista_codigos, user, token, obtener_historial=False):
    """Recorre una lista de códigos posibles en el BCCh hasta encontrar el vigente"""
    url = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
    hoy = datetime.now()
    inicio = hoy - timedelta(days=550)
    
    for codigo in lista_codigos:
        params = {
            "user": user,
            "pass": token,
            "firstdate": inicio.strftime('%Y-%m-%d'),
            "lastdate": hoy.strftime('%Y-%m-%d'),
            "timeseries": codigo,
            "function": "GetSeries"
        }
        try:
            resp = requests.get(url, params=params, timeout=15)
            try:
                data = resp.json()
            except Exception:
                data = json.loads(resp.content.decode('latin-1'))
                
            if data.get('Codigo') == 0:
                observaciones = data.get('Series', {}).get('Obs', [])
                valores_validos = []
                for obs in observaciones:
                    val = obs.get('value')
                    if val is not None and val != 'NaN' and obs.get('statusCode') == 'OK':
                        valores_validos.append((obs.get('indexDateString'), float(val)))
                
                if valores_validos:
                    ultimo_fecha, ultimo_val = valores_validos[-1]
                    print(f"✅ [{codigo}] Dato obtenido: {ultimo_val} (Fecha: {ultimo_fecha})")
                    if obtener_historial:
                        return [v[1] for v in valores_validos]
                    return ultimo_val
            else:
                print(f"⚠️ [{codigo}] Código {data.get('Codigo')}: {data.get('Descripcion')}")
        except Exception as e:
            print(f"🚨 Error técnico en {codigo}: {e}")
    return None

def obtener_datos():
    bcch_user = os.getenv("BCCH_USER", "").strip()
    bcch_token = os.getenv("BCCH_TOKEN", "").strip()

    # Códigos oficiales vigentes del BCCh (incluyendo el desempleo oficial del INE)
    codigos_uf = ["F073.UFF.PRE.Z.D"]
    codigos_dolar = ["F073.TCO.PRE.Z.D"]
    codigos_tpm = ["F022.TPM.TIN.D001.NO.Z.D", "F073.TPM.TIN.Z.D"]
    codigos_ipc_var = ["F074.IPC.VAR.Z.Z.C.M", "F073.IPC.VAR.2023.M"]
    codigos_ipc_v12 = ["G073.IPC.V12.2023.M", "F074.IPC.V12.Z.Z.C.M"]
    codigos_pib_usd = ["F032.PIB.FAA.N.USD.2018.Z.Z.0.T"]
    codigos_desempleo = ["F049.DES.TAS.INE9.10.M"]

    # 1. Consultas directas al Banco Central
    val_uf = consultar_serie_bcch(codigos_uf, bcch_user, bcch_token)
    val_dolar = consultar_serie_bcch(codigos_dolar, bcch_user, bcch_token)
    val_tpm = consultar_serie_bcch(codigos_tpm, bcch_user, bcch_token)
    val_ipc = consultar_serie_bcch(codigos_ipc_var, bcch_user, bcch_token)
    val_inflacion = consultar_serie_bcch(codigos_ipc_v12, bcch_user, bcch_token)
    val_pib = consultar_serie_bcch(codigos_pib_usd, bcch_user, bcch_token)
    val_desempleo = consultar_serie_bcch(codigos_desempleo, bcch_user, bcch_token)

    # 2. Respaldo por si fallara alguna conexión menor
    try:
        resp_min = requests.get("https://mindicador.cl/api", timeout=10).json()
    except Exception:
        resp_min = {}

    if val_tpm is None:
        val_tpm = resp_min.get("tpm", {}).get("valor")

    if val_ipc is None:
        val_ipc = resp_min.get("ipc", {}).get("valor")

    if val_desempleo is None:
        val_desempleo = resp_min.get("tasa_desempleo", {}).get("valor")

    if val_inflacion is None:
        historial_ipc = consultar_serie_bcch(codigos_ipc_var, bcch_user, bcch_token, obtener_historial=True)
        if historial_ipc and len(historial_ipc) >= 12:
            ultimos_12 = historial_ipc[-12:]
            acumulado = 1.0
            for var_m in ultimos_12:
                acumulado *= (1.0 + (var_m / 100.0))
            val_inflacion = round((acumulado - 1.0) * 100.0, 1)

    # 3. Formateo limpio para KWGT
    uf_str = f"${val_uf:,.0f}".replace(",", ".") if val_uf is not None else "N/D"
    dolar_str = f"${val_dolar:,.2f}".replace(",", ".") if val_dolar is not None else "N/D"
    tpm_str = f"{val_tpm}%" if val_tpm is not None else "N/D"
    ipc_str = f"{val_ipc}%" if val_ipc is not None else "N/D"
    inflacion_str = f"{val_inflacion}%" if val_inflacion is not None else "N/D"
    desempleo_str = f"{val_desempleo}%" if val_desempleo is not None else "N/D"
    pib_usd_str = f"{val_pib:,.0f} Millones USD".replace(",", ".") if val_pib is not None else "384.394 Millones USD"

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
