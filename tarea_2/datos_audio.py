"""Descarga el corpus de audio de la Tarea 2 desde Wikimedia Commons y lo deja en WAV mono de 16 kHz.

    .venv/Scripts/python datos_audio.py

Todos los archivos son entrevistas o testimonios en español peruano con licencia CC BY o CC BY-SA 4.0.
Los originales y los WAV quedan en datos/raw/audio/ (fuera de Git); la atribución va a datos/fuentes.csv.
Se respeta una pausa de 1.5 s entre solicitudes y se usa un User-Agent descriptivo.
"""
import time
import urllib.parse
from pathlib import Path

import pandas as pd
import requests
import soundfile as sf

CARPETA = Path(__file__).resolve().parent / "datos" / "raw" / "audio"
SR = 16_000
UA = {"User-Agent": "tarea2-qlab-pucp/1.0 (curso Python intermedio QLAB PUCP; github.com/ecamachoro-bit)"}
API = "https://commons.wikimedia.org/w/api.php"

# id: (archivo en Commons, condición de grabación)
CLIPS = {
    "clip_001": ("Entrevista a Luz Merida-Organización de mujeres indígenas-fiestas patrias-protesta.ogg", "entrevista en exteriores"),
    "clip_002": ("Entrevista-Aurora Coronado-organización de mujeres indígenas-fiestas patrias.ogg", "conferencia de prensa"),
    "clip_003": ("Entrevista 1 en la Av. Rivagüero - El Agustino.ogg", "calle, multihablante"),
    "clip_004": ("Entrevista 2 en la Av. Rivagüero - El Agustino.ogg", "calle, multihablante"),
    "clip_005": ("UNMSM Entrevistas en la marcha 1 por Cristopher Serrano Pérez.wav", "marcha, ruido de multitud"),
    "clip_006": ("UNMSM Entrevista realizada en la marcha por Cristopher Serrano Pérez.wav", "marcha, ruido de multitud"),
    "clip_007": ("Audio de la entrevista a una chica que participaba de la marcha.ogg", "marcha, ruido de multitud"),
    "clip_008": ("Entrevista a la señora Aurelia, mujer shuyasina.ogg", "entrevista en exteriores"),
    "clip_009": ("Entrevista a la señora Dina Espinoza, mujer pomabambina.ogg", "entrevista en exteriores"),
    "clip_010": ("Entrevista a María Romero, organizadora de la fiesta patronal de Tayta Palli de Chuyas.ogg", "entrevista en exteriores"),
    "clip_011": ("Entrevista en el medio tiempo.opus", "estadio, ruido"),
    "clip_012": ("Testimonio N° 5 - Violencia obstétrica en Perú - usuaria de salud.wav", "testimonio grabado"),
    "clip_013": ("Testimonio N°39 - Violencia Obstétrica en el Perú - Servidora de salud.wav", "testimonio grabado"),
    "clip_014": ("Testimonio N° 42-Violencia obstétrica en Perú-Usuaria de salud.wav", "testimonio grabado"),
    "clip_015": ("Testimonio N°25- violencia obstetrica en Perú- Usuaria de salud.wav", "testimonio grabado"),
    "clip_016": ("Testimonio N°13 - Violencia obstétrica en el Perú - Servidora de salud.wav", "testimonio grabado"),
    "clip_017": ("Testimonio N° 37-Violencia obstétrica en Perú-Servidora de Salud.wav", "testimonio grabado"),
    "clip_018": ("Testimonio N° 24-Violencia obstétrica en Perú-Usuaria de salud.wav", "testimonio grabado"),
    "clip_019": ("Testimonio N° 34-Violencia obstétrica en Perú-Usuaria de salud.wav", "testimonio grabado"),
    "clip_020": ("Testimonio N° 19-Violencia obstétrica en Perú-Usuaria de salud.wav", "testimonio grabado"),
    "clip_021": ("Testimonio N° 01-Violencia obstétrica en Perú-Usuaria de salud.wav", "testimonio grabado"),
    "clip_022": ("Testimonio N° 10 - Violencia obstétrica en Perú - Servidora de salud.wav", "testimonio grabado"),
    "clip_023": ("Testimonio N° 15-Violencia obstétrica en Perú- Usuaria de salud.wav", "testimonio grabado"),
    "clip_024": ("Testimonio N°12 - Violencia obstétrica en el Perú - Servidora de salud.wav", "testimonio grabado"),
    "clip_025": ("Testimonio N° 41-Violencia obstétrica en Perú-Servidora de salud.wav", "testimonio grabado"),
    "clip_026": ("Testimonio 3 - Diana Palomino Ramos.ogg", "testimonio grabado"),
    "clip_027": ("Testimonio 2 - Diana Palomino Ramos.ogg", "testimonio grabado"),
    "clip_028": ("Testimonio 4 - Diana Palomino Ramos.ogg", "testimonio grabado"),
}


def _info(titulos):
    """Licencia, autor y URL directa de cada archivo, consultados a la API de Commons."""
    filas = {}
    for i in range(0, len(titulos), 40):
        r = requests.get(API, headers=UA, timeout=60, params=dict(
            action="query", format="json", prop="imageinfo", iiprop="url|extmetadata",
            titles="|".join("File:" + t for t in titulos[i:i + 40]))).json()
        normal = {n["to"]: n["from"] for n in r["query"].get("normalized", [])}
        for p in r["query"]["pages"].values():
            ii = p["imageinfo"][0]
            m = ii["extmetadata"]
            titulo = normal.get(p["title"], p["title"]).removeprefix("File:")
            filas[titulo] = {"url": ii["url"], "pagina": ii["descriptionurl"],
                             "licencia": m["LicenseShortName"]["value"],
                             "autor": pd.Series([m.get("Artist", {}).get("value", "")]).str.replace(r"<[^>]+>", "", regex=True)[0].strip()}
        time.sleep(1.5)
    return filas


def _descargar(url, intentos=5):
    """Si el servidor responde 429 (demasiadas solicitudes), espera cada vez más antes de reintentar."""
    for i in range(intentos):
        r = requests.get(url, headers=UA, timeout=300)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(int(r.headers.get("Retry-After", 10 * (i + 1))))
            continue
        r.raise_for_status()
        return r.content
    raise RuntimeError(f"No se pudo descargar {url}")


def bajar():
    from faster_whisper import decode_audio
    (CARPETA / "originales").mkdir(parents=True, exist_ok=True)
    info = _info([t for t, _ in CLIPS.values()])
    filas = []
    for cid, (titulo, condicion) in CLIPS.items():
        meta = info[titulo]
        original = CARPETA / "originales" / f"{cid}{Path(titulo).suffix.lower()}"
        wav = CARPETA / f"{cid}.wav"
        if not original.exists():
            original.write_bytes(_descargar(meta["url"]))
            time.sleep(1.5)
        if not wav.exists():
            sf.write(wav, decode_audio(str(original), sampling_rate=SR), SR)
        filas.append({"id": cid, "modalidad": "audio", "titulo": titulo, "condicion": condicion,
                      "fuente_url": meta["pagina"], "licencia": meta["licencia"], "autor": meta["autor"],
                      "acceso": f"Descarga directa: {meta['url']} (o ejecutar datos_audio.py)"})
    return pd.DataFrame(filas)


if __name__ == "__main__":
    tabla = bajar()
    print(tabla[["id", "licencia", "titulo"]].to_string(index=False))
