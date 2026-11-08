# Tarea 4 · Agente de investigación: minería formal, minería informal y pobreza (BCRP + ENAHO)

**Estudiante:** Eliana Camacho Cárdenas ([@ecamachoro-bit](https://github.com/ecamachoro-bit)) · Python Intermedio, QLAB PUCP · noviembre de 2026

## 1. Objetivo

Construir un agente en Claude Code que combine un **servidor MCP del BCRP** y **tres Skills de la ENAHO** para
responder, con cifras verificables, esta pregunta:

> **Entre 2015 y 2024, ¿cómo difirió la pobreza monetaria entre los departamentos con minería formal de gran
> escala y aquellos con alta ocupación minera informal y baja producción de oro declarada, en un contexto de
> brecha creciente entre exportación y producción de oro?**

Informe: [`informes/informe_final.md`](informes/informe_final.md).

## 2. Arquitectura

```text
                 pregunta en lenguaje natural
                              │
                     Claude Code (agente)
             ┌────────────────┴────────────────┐
     MCP "bcrp" (mcp/server.py)        Skills (.claude/skills/)
     buscar_series · serie · resumen   limpiando-enaho → salidas/*.parquet, validacion.txt,
     brecha_oro · oro_por_departamento                   serie 2015-2024, empleo minero
     comparar_periodos                 graficando-enaho → figuras/*.png
     recurso bcrp://serie/{codigo}     mapeando-enaho   → mapas/*.png
     prompt informe(tema)
             └────────────────┬────────────────┘
          scripts/indicadores.py (tabla integrada) → informes/informe_final.md
```

Los números siempre los calcula Python (herramientas MCP o scripts de las Skills). El modelo planifica, elige
herramientas, interpreta y redacta.

## 3. Servidor MCP del BCRP (`mcp/server.py`)

| Herramienta | Qué hace |
|---|---|
| `buscar_series` | Busca en el catálogo oficial (17 mil series) por palabras clave y frecuencia |
| `serie` | Descarga una serie entre dos periodos (diaria, mensual, trimestral o anual), sin los "n.d." |
| `resumen` | Primero, último, cambio, variación %, promedio, máximo y mínimo |
| **`brecha_oro`** (propia) | Exportación de oro (PM40098BA) − producción declarada (RD15543DA), en toneladas y % del oro exportado |
| **`oro_por_departamento`** (propia) | Producción de oro de 17 departamentos (RD15544DA…RD15560DA), participación % y cambio, con el código INEI `ccdd` para unir con la ENAHO |
| `comparar_periodos` (propia) | Promedio, mínimo y máximo de una serie en dos intervalos y su variación |
| Recurso `bcrp://serie/{codigo}` | Ficha descriptiva de una serie |
| Prompt `informe(tema)` | Plantilla que obliga a citar código, periodo y fuente y a no estimar |

Decisión de limpieza: PM40098BA dice "millones de onzas troy", pero sus valores (6 514 en 2024) son **miles** de
onzas troy: 6,5 millones de oz ≈ 203 t, que es lo que publican BCRP y SUNAT.

**Pruebas:** `uv run pytest` → **10 passed** (8 originales de la Sesión 04 sin cambios + 2 propias de `brecha_oro`).
Evidencia: [`evidencias_ia/mcp/pruebas.txt`](evidencias_ia/mcp/pruebas.txt).

## 4. Skills (`.claude/skills/`)

| Skill | Scripts | Salidas |
|---|---|---|
| `limpiando-enaho` | `limpiar.py` (2024 completo o `--solo-sumaria` 2015-2023), `serie_pobreza.py`, `empleo_minero.py` | `salidas/validacion.txt`, `validacion_<año>.txt`, parquet, `pobreza_*_2015_2024.csv`, `empleo_minero_2024.csv` |
| `graficando-enaho` | `graficar.py --por area\|sexo\|edad\|departamento\|grupo_minero`, `serie_grupos.py [--brecha]` | `figuras/*.png` |
| `mapeando-enaho` | `mapear.py [--marcar-grupos]` | `mapas/*.png`, `salidas/comparacion_mapa_referencia.csv` |

Reglas de la limpieza: llaves como texto, residentes habituales `((p204==1)&(p205==2))|((p204==2)&(p206==1))`,
`merge(..., validate="m:1")`, ponderación `factor07 × mieperho` (hogares) o `facpob07` (personas), y un informe
`[PASA]/[FALLA]` que detiene el proceso si algo falla. Las Skills de gráficos y mapas piden correr primero
`limpiando-enaho` si no existe la base.

**Validación ENAHO 2024** ([`salidas/validacion.txt`](salidas/validacion.txt)): pobreza 27.58 % (27.6 % INEI),
108,664 residentes habituales, 25/25 departamentos, unión sin duplicados. Los años 2015-2023 también replican la
cifra oficial del INEI (`salidas/validacion_<año>.txt`). El mapa coincide 25/25 con la referencia de la Sesión 16.

**Grupos mineros** ([`referencias/grupos_mineros.csv`](referencias/grupos_mineros.csv)), definidos antes del análisis
con el Excel de fuentes secundarias (MINEM, REINFO) y verificados con ENAHO 2024 módulo 05:

| Grupo | Departamentos |
|---|---|
| A. Formal de gran escala | Áncash, Cajamarca, Ica, Junín, Moquegua, Pasco, Tacna |
| B. Informal con poco oro declarado | Ayacucho, Madre de Dios, Puno |
| C. Mixto | Apurímac, Arequipa, Cusco, La Libertad |
| D. Resto | los otros 11 (incluye Lima, Callao y Huancavelica) |

## 5. Datos

| Fuente | Archivo | Enlace |
|---|---|---|
| INEI ENAHO 2024, módulos 34, 02 y 05 | `datos/966-Modulo34.zip`, `966-Modulo02.zip`, `966-Modulo05.zip` | `https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo34.zip` (cambiar 34 por 02 o 05) |
| INEI ENAHO 2015-2023, módulo 34 | `datos/<código>-Modulo34.zip` | mismos enlaces con códigos 498, 546, 603, 634, 687, 737, 759, 784, 906 |
| Límites departamentales | `datos/peru_departamental_simple.geojson` | [repositorio del curso](https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson) |
| BCRP | vía MCP (API BCRPData) | https://estadisticas.bcrp.gob.pe/estadisticas/series/ |

`datos/` está en `.gitignore` (microdatos pesados). Descarga en Git Bash:

```bash
mkdir -p datos && cd datos
for c in 498 546 603 634 687 737 759 784 906 966; do curl -LO https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/$c-Modulo34.zip; done
curl -LO https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo02.zip
curl -LO https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/966-Modulo05.zip
curl -LO https://raw.githubusercontent.com/d2cml-ai/Data-Science-Python/main/sessions/06-geoespacial/lab/Data/peru_departamental_simple.geojson
cd ..
```

## 6. Instalación con `uv`

```bash
cd tarea_4
uv sync            # crea .venv con fastmcp, pandas, pyarrow, pyreadstat, geopandas, matplotlib, pytest
```

## 7. Conectar el MCP a Claude Code

`.mcp.json` ya lo registra (`uv run --project . mcp/server.py`). Al abrir Claude Code en `tarea_4/` aceptar el
servidor `bcrp`; o bien: `claude mcp add --scope project bcrp -- uv run mcp/server.py`. Comprobar con `/mcp`.

## 8. Reproducir el procesamiento y las pruebas

```bash
bash reproducir.sh          # pruebas MCP + limpieza 2015-2024 + serie + empleo + BCRP + figuras + mapas + indicadores
uv run evaluacion/evaluar.py   # experimento con y sin MCP/Skills (llama a claude -p; ~20 llamadas)
```

## 9. Resultados de la evaluación

Las mismas 10 preguntas (4 BCRP, 4 ENAHO, 2 mixtas), con respuestas fijadas antes de correr a partir de fuentes
oficiales, en sesiones `claude -p` independientes con Sonnet. Detalle en [`evaluacion/comparacion.md`](evaluacion/comparacion.md).

| | Modo A (sin MCP ni Skills) | Modo B (con MCP y Skills) |
|---|---:|---:|
| Correctas | **2/10** | **10/10** |
| No contestadas | 8 | 0 |
| Tiempo promedio | 6.3 s | 52.0 s |

Sin herramientas, el modelo se abstiene en vez de inventar. Una primera corrida del modo B se descartó porque leyó
la respuesta en `preguntas.csv`; se repitió en una copia aislada del proyecto
([`resultados_modoB_descartado.csv`](evaluacion/resultados_modoB_descartado.csv)).

## 10. Limitaciones y problemas encontrados

- **Asociación, no causalidad.** El informe describe diferencias; no atribuye la pobreza a la minería.
- **Clasificación fija.** Los grupos se definieron con datos de 2024-2025 y se aplican a 2015-2024.
- **Informalidad aproximada.** La ENAHO 2024 pública no trae `ocupinf`; se usa un proxy (sin RUC / sin pensión /
  familiar no remunerado). Hay departamentos con menos de 30 mineros en la muestra.
- **Campamentos.** La ENAHO capta a los trabajadores donde residen; en Áncash o Cajamarca el empleo minero formal
  casi no aparece. Por eso A se definió por producción y no por empleo.
- **La brecha del oro es un indicador indirecto** del oro sin origen declarado (informal o ilegal), nacional, no
  departamental.
- **Problemas resueltos:** la sumaria 2022 tardó en descargarse (se reintentó); `float32` en los factores
  producía diferencias de 0.1 pp en el redondeo (se pasó a `float64`); un doble redondeo de CSV (se guardan 4
  decimales); la etiqueta de unidades de PM40098BA es errónea (documentado arriba).

## 11. Ejemplo de una ejecución completa

El agente recibió solo la pregunta y un plan ([`evidencias_ia/integracion/prompt_agente.md`](evidencias_ia/integracion/prompt_agente.md))
en `claude -p` con el MCP y las Skills. Registro completo (stream-json):
[`evidencias_ia/integracion/ejecucion_agente.jsonl`](evidencias_ia/integracion/ejecucion_agente.jsonl); resumen legible:
[`evidencias_ia/integracion/ejecucion_agente.md`](evidencias_ia/integracion/ejecucion_agente.md).

## 12. Evidencias del uso de IA

[`evidencias_ia/`](evidencias_ia/): conversación completa de desarrollo con Claude Code (MCP, Skills, integración,
evaluación y correcciones), exportada a Markdown con correos y tokens ocultos, más las pruebas y la ejecución del
agente.
