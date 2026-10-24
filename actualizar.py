from datetime import datetime
import json
import requests


def obtener_datos():
    url = "https://mindicador.cl/api"
    respuesta = requests.get(url, timeout=10)
    data = respuesta.json()

    # Formatos de valores
    uf_val = f"${data['uf']['valor']:,.0f}".replace(",", ".")
    dolar_val = f"${data['dolar']['valor']:,.2f}".replace(",", ".")
    ipc_val = f"{data['ipc']['valor']}%"

    # La TPM en mindicador.cl a veces requiere extraer el valor directo
    # o usar un valor por defecto si la serie viene vacía ese día
    tpm_num = data.get("tpm", {}).get("valor", None)
    tpm_val = f"{tpm_num}%" if tpm_num is not None else "N/D"

    indicadores = {
        "actualizado": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "uf": uf_val,
        "dolar": dolar_val,
        "ipc": ipc_val,
        "tpm": tpm_val,
    }

    with open("indicadores.json", "w", encoding="utf-8") as f:
        json.dump(indicadores, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    obtener_datos()
