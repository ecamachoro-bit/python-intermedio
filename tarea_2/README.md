# Tarea 2 – Voces y documentos peruanos: del archivo escaneado al texto buscable

**Pregunta del proyecto:** ¿Pueden convertirse documentos escaneados y entrevistas en audio en un archivo de texto estructurado y buscable?

**Dashboard público:** {{URL_DASHBOARD}}

Eliana Camacho (@ecamachoro-bit) · Python intermedio, QLAB PUCP · Tarea 2 individual · octubre de 2026

---

## Qué se hizo

Un pipeline que lleva **25 documentos** y **28 clips de audio** (39,3 min) peruanos a texto buscable y a campos estructurados:

1. **OCR** con PaddleOCR 3.7 (detector PP-OCRv5 mobile + reconocedor PP-OCRv6 medium, `lang=es`).
2. **ASR** con `voz.py` de la Sesión 13: VAD Silero + Whisper large-v3-turbo (faster-whisper, int8 en CPU), **diarización** con huellas WeSpeaker en las entrevistas multihablante y exportación a CSV, SRT y TXT.
3. **Seudonimización** de personas privadas con `voz.seudonimizar` (comparación difusa) y revisión humana: 22 reemplazos en 8 clips, 0 nombres originales en los archivos publicados.
4. **Evaluación** con CER/WER sobre 10 documentos y 10 clips transcritos a mano, con comparación frente a Tesseract (OCR), whisper `small` y NVIDIA Parakeet v3 (ASR).
5. **Extracción estructurada** con Gemini 3.7 Flash (JSON con `null` para datos ausentes) y **auditoría humana** de 20 casos.
6. **Dashboard** en Streamlit que solo lee los CSV (no ejecuta modelos).

## Corpus, fuentes y licencias

Fecha de extracción: **25–26 de octubre de 2026**. El detalle por archivo (URL, licencia, autor y cómo recuperarlo) está en [`datos/fuentes.csv`](datos/fuentes.csv).

| Corpus | Cantidad | Fuente | Licencia |
|---|---|---|---|
| Impresos nítidos | 8 | archive.org: *Mercurio Peruano* (1791), Constitución de 1823, Bases de la Constitución (1822), Carta pastoral (Lima, 1820), *Los pueblos del Perú* (1905), *El problema nacional de la educación pública* (1902), *Istmo de Fitzcarrald* (1903) | Dominio público (anteriores a 1900, o publicados antes de 1930 en EE. UU.) |
| Fotos con sombra o inclinación | 8 | Fotos de celular tomadas por la autora (textos en espacios públicos y páginas de libros) | Capturas propias, sin datos personales. Las páginas de libros conservan los derechos de sus autores: en el dashboard solo se muestra su texto, no la imagen |
| Manuscritos | 9 | 5 escritos a mano por la autora y 4 páginas manuscritas de 1822–1824 (archive.org, John Carter Brown Library) | Propios (CC BY 4.0) / dominio público |
| Audio | 28 clips, 39,3 min | Wikimedia Commons: entrevistas en El Agustino, UNMSM, Fenmucarinap, Chuyas, Pomabamba, estadio y testimonios sobre violencia obstétrica en el Perú | CC BY 4.0 y CC BY-SA 4.0 (autores atribuidos en `fuentes.csv`) |

**Descartes reportados** (detalle en el notebook 01): 3 páginas de archivo en blanco o sin texto, 8 imágenes cuya autoría o licencia no se pudo verificar o que mostraban personas identificables, 1 logo, y audios que no eran español peruano (quechua de Huaylas, Argentina, un hablante venezolano).

## Resultados

{{TABLA_RESULTADOS}}

## Hallazgos

{{HALLAZGOS}}

## Limitaciones técnicas

{{LIMITACIONES}}

## Ética y protección de datos

- Los nombres de personas privadas se reemplazan por `[PERSONA_nn]` en todos los textos publicados (CSV, dashboard y notebooks). El diccionario con los nombres originales está en `datos/raw/seudonimos_privado.json`, que **no** se versiona.
- Algunos títulos de archivo en Wikimedia Commons incluyen el nombre de la persona entrevistada. Las URL se mantienen en `fuentes.csv` porque la licencia exige atribución y permiten recuperar el archivo, pero esos títulos no se copian a los textos.
- El dashboard solo reproduce 4 clips que no mencionan a personas privadas y solo muestra imágenes de dominio público o manuscritos propios.
- Descargas con User-Agent descriptivo y pausas de 1,5 s entre solicitudes.

## Estructura

```
tarea_2/
├── 01_extraccion.ipynb      # corpus, OCR, ASR, seudonimización, limpieza, EDA y exportación
├── 02_evaluacion.ipynb      # referencias manuales, CER/WER, LLM, auditoría, casos difíciles y decisión
├── app.py                   # dashboard Streamlit (solo lee CSV)
├── requirements.txt         # dependencias del dashboard
├── voz.py                   # módulo de la Sesión 13 (VAD, ASR, diarización, seudonimización, métricas)
├── datos_documentos.py      # descarga/copia de los 25 documentos
├── datos_audio.py           # descarga de los 28 clips de Wikimedia Commons
├── procesar_documentos.py   # OCR con PaddleOCR (respaldo crudo + cajas)
├── procesar_audio.py        # ASR + diarización + SRT/TXT
├── procesar_evaluacion.py   # Tesseract, whisper small y Parakeet sobre la muestra fija
├── extraer_llm.py           # extracción estructurada con Gemini
├── seudonimos.py            # aplica el diccionario privado de seudónimos
├── datos/
│   ├── documentos.csv · transcripciones.csv · extraccion_llm.csv · fuentes.csv
│   ├── muestra_evaluacion.csv · referencias/ (transcripciones manuales) · auditoria_llm.csv
│   ├── metricas.csv · metricas_detalle.csv · salidas_eval/ · salidas_llm/
│   └── ejemplos/            # 17 imágenes y 4 audios publicables
├── modelos/                 # tessdata (ignorado)
└── evidencias_ia/           # capturas de la conversación con Claude Code
```

## Cómo ejecutar en local

**Solo el dashboard** (lee los CSV ya generados):

```bash
cd tarea_2
python -m venv .venv
.venv\Scripts\activate          # en macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

**El pipeline completo** (OCR, ASR, evaluación y LLM; descarga ~3 GB de modelos y tarda horas en CPU):

```bash
uv venv --python 3.12 .venv
uv pip install -p .venv pandas plotly streamlit jiwer rapidfuzz soundfile scipy scikit-learn "faster-whisper>=1.2.1" "av<19" \
    "paddleocr>=3.2" "paddlepaddle>=3.2.1" "pyannote-audio>=4.0.7" transformers accelerate pytesseract pillow requests \
    google-genai python-dotenv kaleido ipykernel nbconvert
.venv\Scripts\python datos_audio.py            # 28 clips de Wikimedia Commons
.venv\Scripts\python datos_documentos.py       # 12 páginas de archive.org (+ capturas propias en datos/raw/documentos/propias/)
.venv\Scripts\python procesar_documentos.py    # OCR
.venv\Scripts\python procesar_audio.py         # ASR + diarización
.venv\Scripts\python procesar_evaluacion.py ocr
.venv\Scripts\python procesar_evaluacion.py asr
.venv\Scripts\python extraer_llm.py            # requiere GEMINI_API_KEY en .env
```

Tesseract se instala aparte (`winget install UB-Mannheim.TesseractOCR`) y el modelo de español va en `modelos/tessdata/spa.traineddata` ([tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast)).

## Uso de IA

El proyecto se desarrolló con **Claude Code** como asistente de programación. Las capturas de toda la conversación están en [`evidencias_ia/`](evidencias_ia/). La selección y la toma de fotos y manuscritos propios, las transcripciones manuales de referencia y la auditoría de las extracciones del LLM las hizo la estudiante.
