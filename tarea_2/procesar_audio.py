"""Transcribe el corpus de audio con voz.py (Sesión 13): VAD + faster-whisper + diarización.

    .venv/Scripts/python procesar_audio.py

Por cada clip deja en datos/raw/audio/salidas/ un CSV de segmentos, un SRT y un TXT.
Si la salida de un clip ya existe, no lo vuelve a transcribir (así el notebook puede reutilizarla).
"""
import json
import time
from pathlib import Path

import pandas as pd

from voz import SR, Transcriptor, a_srt, a_tabla, a_texto, cargar_audio, diarizar, Segmento

AUDIO = Path(__file__).resolve().parent / "datos" / "raw" / "audio"
SALIDAS = AUDIO / "salidas"
MODELO = "faster-whisper"  # large-v3-turbo en CTranslate2, int8 en CPU
MULTIHABLANTE = {"clip_003": None, "clip_004": None}  # None: el número de hablantes lo decide el umbral


def procesar(cid: str, tr: Transcriptor) -> dict:
    meta = SALIDAS / f"{cid}.json"
    if meta.exists():
        return json.loads(meta.read_text(encoding="utf-8"))
    audio = cargar_audio(str(AUDIO / f"{cid}.wav"))
    t0 = time.perf_counter()
    segs = tr.segmentos(audio, idioma="es")
    seg_asr = time.perf_counter() - t0
    if cid in MULTIHABLANTE and segs:
        segs = diarizar(audio, segs, n_hablantes=MULTIHABLANTE[cid])
    tabla = a_tabla(segs)
    tabla.to_csv(SALIDAS / f"{cid}.csv", index=False)
    (SALIDAS / f"{cid}.srt").write_text(a_srt(segs), encoding="utf-8")
    (SALIDAS / f"{cid}.txt").write_text(a_texto(segs), encoding="utf-8")
    info = {"id": cid, "duracion_seg": round(len(audio) / SR, 1), "segundos_proceso": round(seg_asr, 1),
            "n_segmentos": len(segs), "n_hablantes": tabla["hablante"].nunique() if cid in MULTIHABLANTE else 1,
            "modelo_asr": f"{tr.info['nombre']} ({tr.info['hf']}, int8 CPU, VAD Silero, beam 5, idioma=es)"}
    meta.write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    return info


if __name__ == "__main__":
    SALIDAS.mkdir(parents=True, exist_ok=True)
    tr = Transcriptor(MODELO)
    print(tr, f"cargado en {tr.segundos_carga:.0f} s", flush=True)
    for wav in sorted(AUDIO.glob("clip_*.wav")):
        info = procesar(wav.stem, tr)
        print(info["id"], info["duracion_seg"], "s ->", info["segundos_proceso"], "s", flush=True)
