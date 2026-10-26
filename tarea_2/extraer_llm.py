"""Extracción estructurada con un LLM (Gemini) a partir de los textos OCR y ASR ya seudonimizados.

    .venv/Scripts/python extraer_llm.py

Lee datos/documentos.csv y datos/transcripciones.csv, guarda una respuesta JSON por registro en
datos/salidas_llm/ (caché) y arma datos/extraccion_llm.csv con id, modalidad, campos_json, modelo_llm, fecha.
La clave va en .env (GEMINI_API_KEY), que no se versiona.
"""
import json
import os
import time
from datetime import date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
CACHE = RAIZ / "datos" / "salidas_llm"
MODELOS = ["gemini-3.7-flash", "gemini-3.5-flash-lite"]  # el segundo solo si el primero agota la cuota

PROMPT = """Eres un asistente de archivística. Recibes el texto extraído automáticamente (OCR o transcripción de audio)
de un {modalidad} peruano. El texto puede tener errores de reconocimiento.

Devuelve SOLO un objeto JSON con estas claves:
- "modalidad": "{modalidad}"
- "tema": tema principal en 2 a 6 palabras
- "resumen": una o dos oraciones fieles al texto
- "idioma": idioma predominante (código ISO 639-1)
{campos}
Reglas: usa null cuando el dato NO aparezca explícitamente en el texto. No inventes ni deduzcas datos que no estén.
Si el texto es ilegible o casi vacío, dilo en "resumen" y deja el resto en null. Los marcadores [PERSONA_n] son
seudónimos: cópialos tal cual, nunca intentes adivinar el nombre real.

TEXTO:
\"\"\"{texto}\"\"\"
"""
CAMPOS = {
    "documento": """- "tipo_documento": por ejemplo ley, carta, informe, poema, aviso, índice (null si no se puede saber)
- "emisor": persona o institución que emite el documento, solo si aparece
- "fecha": fecha que aparece en el texto (tal como está escrita), solo si aparece
- "monto": cantidad de dinero que aparece en el texto, solo si aparece""",
    "audio": """- "numero_hablantes": número de hablantes si se puede sustentar con el texto (marcas [HABLANTE_n] o un diálogo evidente), si no null
- "citas_clave": lista de 1 a 3 frases textuales importantes copiadas del texto, o null""",
}


def _cliente():
    from google import genai
    load_dotenv(RAIZ / ".env")
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def extraer(cliente, rid, modalidad, texto):
    CACHE.mkdir(parents=True, exist_ok=True)
    ruta = CACHE / f"{rid}.json"
    if ruta.exists():
        return json.loads(ruta.read_text(encoding="utf-8"))
    from google.genai import types
    prompt = PROMPT.format(modalidad=modalidad, campos=CAMPOS[modalidad], texto=texto[:12000])
    for modelo in MODELOS:
        for intento in range(4):
            try:
                r = cliente.models.generate_content(model=modelo, contents=prompt, config=types.GenerateContentConfig(
                    temperature=0, response_mime_type="application/json"))
                salida = {"id": rid, "modalidad": modalidad, "campos": json.loads(r.text), "modelo_llm": modelo,
                          "fecha": date.today().isoformat()}
                ruta.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
                return salida
            except Exception as e:  # 429 (cuota) o 503: esperar y reintentar; si persiste, pasar al siguiente modelo
                print(rid, modelo, type(e).__name__, str(e)[:120], flush=True)
                time.sleep(5 * (intento + 1))
    raise RuntimeError(f"Sin respuesta para {rid}")


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    cliente = _cliente()
    docs = pd.read_csv(RAIZ / "datos" / "documentos.csv").assign(modalidad="documento", texto=lambda d: d["texto_ocr"])
    aud = pd.read_csv(RAIZ / "datos" / "transcripciones.csv").assign(modalidad="audio", texto=lambda d: d["texto_asr"])
    filas = []
    for f in pd.concat([docs, aud]).itertuples():
        s = extraer(cliente, f.id, f.modalidad, str(f.texto) if pd.notna(f.texto) else "")
        filas.append({"id": s["id"], "modalidad": s["modalidad"], "campos_json": json.dumps(s["campos"], ensure_ascii=False),
                      "modelo_llm": f"{s['modelo_llm']} (temperature=0, salida JSON)", "fecha": s["fecha"]})
        print(f.id, "ok", flush=True)
    tabla = pd.DataFrame(filas)
    tabla.to_csv(RAIZ / "datos" / "extraccion_llm.csv", index=False)
    return tabla


if __name__ == "__main__":
    main()
