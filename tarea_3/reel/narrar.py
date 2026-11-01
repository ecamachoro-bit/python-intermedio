"""Narra cada escena de guion.json con la voz clonada (Qwen3-TTS) y la controla con Whisper.

Uso: python narrar.py --voz recursos/mi_nota.ogg --modelo RUTA_AL_MODELO [--prueba]
Salidas: salidas/escena_N.wav y salidas/guion_narrado.json. Basado en el flujo de la Sesión 15.
"""
import argparse
import json
import pathlib
import re
import subprocess

import imageio_ffmpeg
import jiwer
import numpy as np
import soundfile as sf
import torch
from faster_whisper import WhisperModel
from num2words import num2words
from qwen_tts import Qwen3TTSModel

aqui = pathlib.Path(__file__).parent
sal = aqui / "salidas"
sal.mkdir(exist_ok=True)
ap = argparse.ArgumentParser()
ap.add_argument("--voz", required=True)
ap.add_argument("--modelo", default="Qwen/Qwen3-TTS-12Hz-0.6B-Base")
ap.add_argument("--prueba", action="store_true")
ap.add_argument("--max-error", type=float, default=0.22)
a = ap.parse_args()


def hablado(frase):
    return re.sub(r"\{([^|}]+)\|[^}]+\}", r"\1", frase)


def normalizar(t):
    t = re.sub(r"(\d)[.,](?=\d{3}\b)", r"\1", t)
    t = re.sub(r"\d+", lambda m: num2words(int(m.group()), lang="es"), t)
    return " ".join(jiwer.RemovePunctuation()(t.lower()).split())


ff = imageio_ffmpeg.get_ffmpeg_exe()
subprocess.run([ff, "-y", "-loglevel", "error", "-i", a.voz, "-ac", "1", "-ar", "24000", str(sal / "referencia.wav")], check=True)
ref, sr_ref = sf.read(sal / "referencia.wav", dtype="float32")
print(f"referencia: {len(ref) / sr_ref:.1f} s", flush=True)
whisper = WhisperModel("small", device="cpu", compute_type="int8")
a16 = np.interp(np.arange(0, len(ref), sr_ref / 16000), np.arange(len(ref)), ref).astype(np.float32)
ref_texto = " ".join(s.text.strip() for s in whisper.transcribe(a16, language="es", beam_size=5)[0])
print("texto de referencia:", ref_texto, flush=True)
tts = Qwen3TTSModel.from_pretrained(a.modelo, device_map="cpu", dtype=torch.float32)
prompt = tts.create_voice_clone_prompt(ref_audio=(ref, sr_ref), ref_text=ref_texto)


def escuchar(audio, sr):
    x = np.interp(np.arange(0, len(audio), sr / 16000), np.arange(len(audio)), audio).astype(np.float32)
    return " ".join(s.text for s in whisper.transcribe(x, language="es")[0])


def decir(texto, destino, intentos=3):
    mejor = None
    if destino.exists():
        au, sr = sf.read(destino, dtype="float32")
        err = jiwer.wer(normalizar(texto), normalizar(escuchar(au, sr)))
        print(f"  ya existía: {len(au) / sr:.1f} s, error {err:.0%}", flush=True)
        if err <= a.max_error:
            return len(au) / sr, err
    for n in range(1, intentos + 1):
        wavs, sr = tts.generate_voice_clone(text=texto, language="Spanish", voice_clone_prompt=prompt)
        au = np.asarray(wavs[0], dtype=np.float32)
        oido = escuchar(au, sr)
        err = jiwer.wer(normalizar(texto), normalizar(oido))
        print(f"  intento {n}: {len(au) / sr:.1f} s, error {err:.0%} | {oido.strip()}", flush=True)
        if mejor is None or err < mejor[0]:
            mejor = (err, au, sr)
            sf.write(destino, au, sr)
        if err <= a.max_error:
            break
    return len(mejor[1]) / mejor[2], mejor[0]


if a.prueba:
    print(decir("Hola, esta es una prueba de mi voz clonada para el reel sobre minería informal.", sal / "prueba_voz.wav"))
    raise SystemExit
guion = json.loads((aqui / "guion.json").read_text(encoding="utf-8"))
for i, e in enumerate(guion["escenas"], 1):
    print(f"escena {i}: {hablado(e['frase'])[:70]}", flush=True)
    e["duracion"], e["error_whisper"] = decir(hablado(e["frase"]), sal / f"escena_{i}.wav")
    (sal / "guion_narrado.json").write_text(json.dumps(guion, ensure_ascii=False, indent=2), encoding="utf-8")
print("total", round(sum(e["duracion"] for e in guion["escenas"]), 1), "s", flush=True)
