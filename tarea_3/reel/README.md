# Reel

Video vertical de 1080 × 1920 con narración clonada de mi propia voz, mapas, gráficos animados con los datos del proyecto, música y subtítulos.

| Archivo | Qué es |
|---|---|
| `reel.mp4` | Video final |
| `guion.json` | Guion por escenas, con la verificación de cada cifra |
| `subtitulos.srt` | Subtítulos sincronizados |
| `portada.png` | Cuadro de muestra |
| `recursos/musica.wav` | Música original generada por `armar_reel.py` a partir de ondas simples; no usa obras de terceros |
| `publicacion_y_entrega.md` | Texto de LinkedIn y comentario de entrega |

## Cómo reproducirlo

Sigue el flujo de la [Sesión 15](https://github.com/d2cml-ai/Data-Science-Python/tree/main/sessions/15-texto-a-reel). Se necesita un entorno con `qwen-tts faster-whisper pillow imageio-ffmpeg soundfile jiwer num2words`, y Selenium con Chrome para las capturas.

```bash
python capturar_visuales.py                                 # imágenes del dashboard y mapas
python narrar.py --voz recursos/mi_voz.ogg                  # voz clonada con Qwen3-TTS, controlada con Whisper
python armar_reel.py                                        # mezcla, subtítulos y video
```

La grabación original de mi voz (17.4 s) no se publica. Las imágenes satelitales provienen de Esri World Imagery y se muestran en el video con su crédito.
