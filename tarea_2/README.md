# Tarea 2 – Voces y documentos peruanos: del archivo escaneado al texto buscable

**Pregunta del proyecto:** ¿Pueden convertirse documentos escaneados y entrevistas en audio en un archivo de texto estructurado y buscable?

> 🚧 En construcción. Este README se completará con el corpus, las fuentes y licencias, los hallazgos, las limitaciones y el enlace al dashboard.

## Estructura

```
tarea_2/
├── 01_extraccion.ipynb        # OCR, transcripción, seudonimización, limpieza y EDA
├── 02_evaluacion.ipynb        # CER/WER, extracción con LLM y comparativa de modelos
├── app.py                     # Dashboard en Streamlit
├── voz.py                     # Módulo de la Sesión 13 (VAD, ASR, diarización, seudonimización, métricas)
├── requirements.txt
├── datos/
│   ├── documentos.csv
│   ├── transcripciones.csv
│   ├── extraccion_llm.csv
│   ├── fuentes.csv
│   └── ejemplos/
├── modelos/
└── evidencias_ia/
```

`voz.py` proviene de la Sesión 13 del curso ([d2cml-ai/Data-Science-Python](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/13-audio-a-texto)).
