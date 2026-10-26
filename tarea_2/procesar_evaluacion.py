"""Corre los modelos de comparación sobre la muestra fija de evaluación (Parte 2).

    .venv/Scripts/python procesar_evaluacion.py ocr      # Tesseract sobre los 10 documentos
    .venv/Scripts/python procesar_evaluacion.py asr      # whisper small (base) y Parakeet v3 sobre los 10 clips

La muestra se fijó en datos/muestra_evaluacion.csv ANTES de calcular cualquier métrica, y las
configuraciones de abajo tampoco se cambian después de verlas. Cada salida (texto + segundos) queda en
datos/salidas_eval/<modelo>.csv. PaddleOCR y Whisper turbo + VAD se toman de la Parte 1.
"""
import os
import sys
import time
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent
MUESTRA = pd.read_csv(RAIZ / "datos" / "muestra_evaluacion.csv")
SALIDAS = RAIZ / "datos" / "salidas_eval"
TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def _guardar(nombre, filas):
    SALIDAS.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(filas).to_csv(SALIDAS / f"{nombre}.csv", index=False)


def tesseract():
    """Tesseract 5 con el modelo rápido de español (tessdata_fast) y segmentación automática (--psm 3)."""
    import pytesseract
    from PIL import Image, ImageOps
    pytesseract.pytesseract.tesseract_cmd = TESSERACT
    os.environ["TESSDATA_PREFIX"] = str(RAIZ / "modelos" / "tessdata")  # --tessdata-dir falla con espacios en la ruta
    config = "--psm 3"
    filas = []
    for did in MUESTRA.query("modalidad == 'documento'")["id"]:
        ruta = next((RAIZ / "datos" / "raw" / "documentos").glob(f"{did}.*"))
        imagen = ImageOps.exif_transpose(Image.open(ruta))
        t0 = time.perf_counter()
        texto = pytesseract.image_to_string(imagen, lang="spa", config=config)
        filas.append({"id": did, "texto": " ".join(texto.split()), "segundos": round(time.perf_counter() - t0, 2),
                      "modelo": f"Tesseract {pytesseract.get_tesseract_version()} (spa, tessdata_fast, psm 3)"})
        print(did, filas[-1]["segundos"], "s", flush=True)
    _guardar("tesseract", filas)


def asr():
    from voz import SR, Transcriptor, cargar_audio
    clips = MUESTRA.query("modalidad == 'audio'")["id"].tolist()
    audios = {c: cargar_audio(str(RAIZ / "datos" / "raw" / "audio" / f"{c}.wav")) for c in clips}

    # Línea base: faster-whisper small en CPU, configuración por defecto (sin VAD)
    from faster_whisper import WhisperModel
    t0 = time.perf_counter()
    modelo = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=min(8, os.cpu_count() or 4))
    carga = time.perf_counter() - t0
    filas = []
    for c, x in audios.items():
        t0 = time.perf_counter()
        segs, _ = modelo.transcribe(x, language="es")
        texto = " ".join(s.text.strip() for s in segs)
        filas.append({"id": c, "texto": texto, "segundos": round(time.perf_counter() - t0, 1), "duracion_seg": round(len(x) / SR, 1),
                      "modelo": "faster-whisper small (int8 CPU, sin VAD, beam 5 por defecto)", "carga_seg": round(carga, 1)})
        print("small", c, filas[-1]["segundos"], "s", flush=True)
    _guardar("whisper_small", filas)
    del modelo

    # Alternativo: NVIDIA Parakeet TDT 0.6B v3 (transductor, no genera texto en silencios), tramos por VAD
    tr = Transcriptor("parakeet-v3", device="cpu")
    filas = []
    for c, x in audios.items():
        t0 = time.perf_counter()
        texto = " ".join(s.texto for s in tr.segmentos(x))
        filas.append({"id": c, "texto": texto, "segundos": round(time.perf_counter() - t0, 1), "duracion_seg": round(len(x) / SR, 1),
                      "modelo": "Parakeet TDT 0.6B v3 (NVIDIA, CPU float32, tramos VAD Silero)", "carga_seg": round(tr.segundos_carga, 1)})
        print("parakeet", c, filas[-1]["segundos"], "s", flush=True)
    _guardar("parakeet_v3", filas)


if __name__ == "__main__":
    {"ocr": tesseract, "asr": asr}[sys.argv[1]]()
