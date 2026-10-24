import os
import json
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def consultar_serie_bcch(lista_codigos, user, token, obtener_historial=False):
    """Recorre una lista de códigos posibles en el BCCh hasta encontrar el vigente"""
    url = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
    hoy = datetime.now()
    # Pedimos 450 días para asegurar al menos 13 meses de datos en series mensuales
    inicio = hoy - timedelta(days=450)
    
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
            # Forzamos decodificación compatible con tildes del BCCh si falla UTF-8
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

    # Listas con los códigos oficiales vigentes del BCCh (incluyendo nueva base IPC 2023=100)
    codigos_uf = ["F073.UFF.PRE.Z.D"]
    codigos_dolar = ["F073.TCO.PRE.Z.D"]
    codigos_tpm = ["F022.TPM.TIN.D001.NO.Z.D", "F073.TPM.TIN.Z.D"]
    codigos_ipc_var = ["F074.IPC.VAR.Z.Z.C.M", "F073.IPC.VAR.2023.M", "F073.IPC.VAR.Z.Z.C.M"]
    codigos_ipc_v12 = ["F074.IPC.V12.Z.Z.C.M", "F073.IPC.V12.2023.M", "F073.IPC.V12.Z.Z.C.M"]

    # 1. Consultas directas al Banco Central
    val_uf = consultar_serie_bcch(codigos_uf, bcch_user, bcch_token)
    val_dolar = consultar_serie_bcch(codigos_dolar, bcch_user, bcch_token)
    val_tpm = consultar_serie_bcch(codigos_tpm, bcch_user, bcch_token)
    val_ipc = consultar_serie_bcch(codigos_ipc_var, bcch_user, bcch_token)
    val_inflacion = consultar_serie_bcch(codigos_ipc_v12, bcch_user, bcch_token)

    # 2. Respaldo inteligente para TPM, IPC e Inflación (y Desempleo del INE)
    try:
        resp_min = requests.get("https://mindicador.cl/api", timeout=10).json()
    except Exception:
        resp_min = {}

    if val_tpm is None:
        val_tpm = resp_min.get("tpm", {}).get("valor")
        print(f"🔄 [TPM] Obtenida desde respaldo: {val_tpm}")

    if val_ipc is None:
        val_ipc = resp_min.get("ipc", {}).get("valor")
        print(f"🔄 [IPC] Obtenido desde respaldo: {val_ipc}")

    # Si el BCCh no entrega la variación a 12 meses directa, la calculamos con los últimos 12 meses de IPC
    if val_inflacion is None:
        historial_ipc = consultar_serie_bcch(codigos_ipc_var, bcch_user, bcch_token, obtener_historial=True)
        if historial_ipc and len(historial_ipc) >= 12:
            ultimos_12 = historial_ipc[-12:]
            acumulado = 1.0
            for var_m in ultimos_12:
                acumulado *= (1.0 + (var_m / 100.0))
            val_inflacion = round((acumulado - 1.0) * 100.0, 1)
            print(f"🧮 [Inflación 12M] Calculada desde serie BCCh: {val_inflacion}%")
        else:
            # Cálculo con los últimos 12 meses de la serie IPC si el código de serie varió
            try:
                hist_min = requests.get("https://mindicador.cl/api/ipc", timeout=10).json().get("serie", [])
                if len(hist_min) >= 12:
                    acumulado = 1.0
                    for item in hist_min[:12]:
                        acumulado *= (1.0 + (float(item["valor"]) / 100.0))
                    val_inflacion = round((acumulado - 1.0) * 100.0, 1)
                    print(f"🧮 [Inflación 12M] Calculada exactamente (12 meses): {val_inflacion}%")
            except Exception as e:
                print(f"Error calculando inflación 12M: {e}")

    desempleo_num = resp_min.get("tasa_desempleo", {}).get("valor")
    
    # 3. Formateo limpio para KWGT
    uf_str = f"${val_uf:,.0f}".replace(",", ".") if val_uf is not None else "N/D"
    dolar_str = f"${val_dolar:,.2f}".replace(",", ".") if val_dolar is not None else "N/D"
    tpm_str = f"{val_tpm}%" if val_tpm is not None else "N/D"
    ipc_str = f"{val_ipc}%" if val_ipc is not None else "N/D"
    inflacion_str = f"{val_inflacion}%" if val_inflacion is not None else "N/D"
    desempleo_str = f"{round(float(desempleo_num), 2)}%" if desempleo_num is not None else "N/D"
    pib_usd_str = "335.000 Millones USD"

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
