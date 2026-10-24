import json
from datetime import datetime
import requests


def obtener_datos():
    url = "https://mindicador.cl/api"
    respuesta = requests.get(url, timeout=10)
    data = respuesta.json()

    # Formateamos los números para que se lean bien en pantalla
    uf_val = f"${data['uf']['valor']:,.0f}".replace(",", ".")
    dolar_val = f"${data['dolar']['valor']:,.2f}".replace(",", ".")
    ipc_val = f"{data['ipc']['valor']}%"
    tpm_val = f"{data['tpm']['valor']}%"

    indicadores = {
        "actualizado": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "uf": uf_val,
        "dolar": dolar_val,
        "ipc": ipc_val,
        "tpm": tpm_val,
    }

    # Guardamos todo en un archivo JSON pequeño
    with open("indicadores.json", "w", encoding="utf-8") as f:
        json.dump(indicadores, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    obtener_datos()
