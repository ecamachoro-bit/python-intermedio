---
name: mapeando-enaho
description: Hace un mapa coroplético de la pobreza monetaria o extrema de la ENAHO del INEI por departamento del Perú, unido por código de ubigeo, con la opción de marcar los grupos mineros. Úsala cuando pidan un mapa, mapear o ver la pobreza por departamento o región en el territorio.
---

# Mapear la ENAHO

1. Si no existe `salidas/hogares_2024.parquet`, usa primero la skill `limpiando-enaho`.
2. Si falta `datos/peru_departamental_simple.geojson`, pide bajarlo de
   https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson
3. Desde la raíz del proyecto, corre exactamente:
   `uv run ${CLAUDE_SKILL_DIR}/scripts/mapear.py`
   - Pobreza extrema: agrega `--indicador pobre_extremo`.
   - Con los grupos mineros (borde de color y letra A/B/C/D): agrega `--marcar-grupos`.
4. Muestra la ruta del mapa, los tres departamentos con más y menos pobreza y la comparación con la referencia de
   la Sesión 16 (`salidas/comparacion_mapa_referencia.csv`, deben coincidir 25/25). Si no coincide, el script se
   detiene: revisa la unión, no corrijas a mano.

## Reglas fijas (ya están en el script)

- Une por código: `ubigeo[:2]` con `FIRST_IDDP`, con `validate="1:1"`. Nunca por nombre.
- Exige 25 departamentos y ninguno sin dato; Lima (15) y Callao (07) van separados.
- Pondera con `factor07 × mieperho`.
- Un solo color de claro a oscuro, desde 0; nunca arcoíris. Leyenda con la unidad: «% de personas».
- Nota al pie con la fuente. PNG a 200 dpi en `mapas/`.
