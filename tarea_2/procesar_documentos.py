"""OCR del corpus de documentos con PaddleOCR (Sesión 10).

    .venv/Scripts/python procesar_documentos.py

Por cada documento guarda en datos/raw/documentos/ocr/ el resultado crudo (JSON con textos, confianzas
y cajas) y una imagen con las cajas detectadas (los "recortes"). Si ya existe, no repite el OCR.
"""
import json
import os
import time
from pathlib import Path

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

DOCS = Path(__file__).resolve().parent / "datos" / "raw" / "documentos"
SALIDAS = DOCS / "ocr"
OPCIONES = dict(
    lang="es",
    text_detection_model_name="PP-OCRv5_mobile_det",  # detector ligero: el "server" tarda ~7 min por página en esta CPU
    use_doc_orientation_classify=False,   # no girar la página completa
    use_doc_unwarping=False,              # no "planchar" hojas dobladas
    use_textline_orientation=False,       # no girar cada línea
    enable_mkldnn=False,                  # oneDNN falla en Windows con PaddlePaddle 3.x (NotImplementedError PIR)
)
NOMBRE_MODELO = "PaddleOCR {v} (PP-OCRv5 mobile det + PP-OCRv6 medium rec, lang=es, sin orientación ni unwarping, CPU)"


def cargar():
    import paddleocr
    from paddleocr import PaddleOCR
    return PaddleOCR(device="cpu", **OPCIONES), NOMBRE_MODELO.format(v=paddleocr.__version__)


def leer(ruta: Path, ocr) -> dict:
    """OCR de una imagen. Devuelve líneas, confianzas y segundos; guarda el respaldo crudo."""
    crudo = SALIDAS / f"{ruta.stem}.json"
    if crudo.exists():
        return json.loads(crudo.read_text(encoding="utf-8"))
    t0 = time.perf_counter()
    r = ocr.predict(str(ruta))[0]
    segundos = time.perf_counter() - t0
    r.save_to_img(str(SALIDAS / "cajas"))
    salida = {"id": ruta.stem, "lineas": list(r["rec_texts"]), "confianzas": [round(float(s), 3) for s in r["rec_scores"]],
              "cajas": [list(map(int, c)) for c in r["rec_boxes"]], "segundos": round(segundos, 1)}
    crudo.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    return salida


if __name__ == "__main__":
    import sys
    (SALIDAS / "cajas").mkdir(parents=True, exist_ok=True)
    ocr, nombre = cargar()
    print(nombre, flush=True)
    rutas = [DOCS / a for a in sys.argv[1:]] or sorted(DOCS.glob("doc_*.*"))
    for ruta in rutas:
        s = leer(ruta, ocr)
        print(s["id"], len(s["lineas"]), "líneas,", s["segundos"], "s |", " ".join(s["lineas"])[:120], flush=True)
