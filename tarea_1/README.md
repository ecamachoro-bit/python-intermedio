# 🗞️ Tarea 1 – Noticias peruanas: del titular al clasificador

## 1. Pregunta del proyecto
**¿Pueden convertir titulares peruanos en un clasificador de noticias?**

Sí. Con 383 titulares de El Comercio etiquetados por sección editorial y validados con un LLM, un modelo DistilBERT
multilingüe ajustado alcanza **F1 macro de 0.841 en un conjunto de test nunca visto**, frente a 0.577 del modelo
zero-shot sin entrenar.

## 2. Medio y fechas de extracción
- **Medio:** El Comercio (opción B).
- **Fuente:** sitemaps de noticias por sección declarados en `robots.txt`
  (`https://elcomercio.pe/sitemap/news/{politica|economia|deporte-total|tecnologia}/?outputType=xml`).
  El RSS oficial solo devolvía 13–17 noticias por sección, por lo que se documentó y se usó el sitemap.
  La bajada se obtuvo de `og:description` de cada artículo (User-Agent descriptivo, pausa de 1.5 s, máx. 1 reintento).
- **Fecha de descarga:** 18/10/2026. **Rango de publicación:** 06/10/2026 – 18/10/2026.
- **Volumen:** 400 descargadas → **383 finales** (1 URL duplicada, 16 fuera de las 4 categorías).

| Categoría | Noticias |
|---|---|
| economia | 99 |
| deportes | 98 |
| ciencia_tecnologia | 95 |
| politica | 91 |

## 3. Resultados
| Modelo | Accuracy (test) | F1 macro (test) | Latencia |
|---|---|---|---|
| Zero-shot (`Recognai/bert-base-spanish-wwm-cased-xnli`) | 0.690 | 0.685 | ~0.21 s/titular |
| LLM débil (`gemini-3.7-flash` + `gemini-3.5-flash-lite`) | 0.966 | 0.965 | ~0.2 s/titular en lotes (estimada) |
| **DistilBERT fine-tuned** (`distilbert/distilbert-base-multilingual-cased`) | **0.845** | **0.841** | **~0.03 s/titular** |

- Línea base zero-shot sobre 40 titulares: **F1 macro 0.577** (accuracy 0.600).
- Acuerdo LLM–Humano (auditoría a ciegas de 20 casos): **19/20 (95%)**.
- Split estratificado 70/15/15 con `random_state=42`: 267 / 58 / 58. Se entrenó con las 246 noticias de train donde la
  sección editorial y el LLM coinciden (supervisión débil); validación y test no se filtraron.

## 4. Hallazgos analíticos
1. **Economía es la categoría más difícil (F1 0.69) por el formato de entrevista.** Muchas notas económicas de El Comercio
   se titulan "Nombre, cargo: «cita»", el mismo patrón que domina en política; por eso el modelo envía economía a política
   (recall de economía 0.60, recall de política 1.00). Deportes, en cambio, es casi perfecto (F1 0.97) por su vocabulario exclusivo.
2. **El LLM es el más preciso, pero no el más práctico.** Gemini logra F1 0.965, pero en esta misma tarea sufrió errores
   503 (saturación) y 429 (cuota diaria de 20 solicitudes agotada). DistilBERT, gratis y local, responde ~8 veces más rápido.
   La mejor estrategia es usar el LLM para etiquetar y limpiar datos, y DistilBERT para servir predicciones.

## 5. Limitaciones técnicas
1. **Sesgo temporal y tamaño pequeño:** los sitemaps solo exponen las ~100 noticias más recientes por sección; deportes
   cubre solo 3 días y ciencia y tecnología 13. El test tiene 58 noticias, así que cada error mueve el F1 ~1–2 puntos.
2. **Etiquetas por sección editorial:** la "verdad" proviene de dónde publicó el diario, no de una anotación experta.
   Hay casos ambiguos (p. ej., regulación de gafas inteligentes publicada en tecnología) y la auditoría humana discrepó en 1/20.
   El probador solo usa el titular, sin la bajada.

## 6. Cómo ejecutar en local
```bash
cd tarea_1
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```
- El modelo entrenado (`modelo/model.safetensors`, ~540 MB) **no se sube a GitHub** por el límite de 100 MB. Para
  regenerarlo, ejecuta `02_clasificacion.ipynb` (≈5 min en CPU); se guarda en `modelo/`.
- Para volver a etiquetar con el LLM, crea un archivo `.env` con `GEMINI_API_KEY=tu_clave` (excluido por `.gitignore`)
  y borra `datos/etiquetas_llm.csv`.

## Estructura
```text
tarea_1/
├── 01_recoleccion.ipynb     # Scraping (sitemaps), limpieza, mapeo y EDA
├── 02_clasificacion.ipynb   # Zero-shot, LLM + auditoría, split, fine-tuning, evaluación y comparativa
├── app.py                   # Dashboard Streamlit
├── requirements.txt
├── datos/
│   ├── noticias.csv         # 383 noticias, 7 columnas
│   ├── etiquetas_llm.csv    # titular, etiqueta_llm, confianza, modelo_llm, fecha
│   ├── auditoria_llm.csv    # 20 casos revisados manualmente
│   └── raw/                 # respaldo crudo: robots.txt, sitemaps XML, noticias_crudo.csv
└── modelo/                  # config, tokenizer y metricas.json (pesos excluidos)
```
