# Comparación: Claude Code sin y con MCP + Skills

**Diseño.** Las mismas 10 preguntas (`preguntas.csv`: 4 BCRP, 4 ENAHO, 2 mixtas), con respuestas esperadas fijadas
**antes** de correr a partir del INEI (informes técnicos de pobreza, referencia de la Sesión 16) y de la API del
BCRP consultada con `curl` (independiente del MCP). Tolerancias fijas por pregunta; en las mixtas además debe
identificar el departamento correcto. Mismo modelo (Sonnet), misma instrucción, una sesión independiente por
pregunta (`claude -p --no-session-persistence`). Script: `evaluar.py`. Resultados: `resultados.csv`.

| | Modo A · sin MCP ni Skills | Modo B · con MCP y Skills |
|---|---|---|
| Herramientas habilitadas | Ninguna (`--tools ""`, sin MCP, Skill bloqueada) | MCP `bcrp` + Skills + Bash, Read, Glob, Grep |
| Carpeta de trabajo | Carpeta temporal vacía (no ve el proyecto) | Copia del proyecto **sin** `evaluacion/` ni `evidencias_ia/` |

## Resultados

| | Modo A | Modo B |
|---|---:|---:|
| **Correctas** | **2/10** | **10/10** |
| Incorrectas | 0 | 0 |
| No contestadas ("no sabe", valor null) | 8 | 0 |
| BCRP / ENAHO / Mixtas correctas | 0/4 · 2/4 · 0/2 | 4/4 · 4/4 · 2/2 |
| Tiempo promedio por pregunta | 6.3 s | 52.0 s (mediana 31.2 s) |
| Llamadas a herramientas por pregunta | 0 | 3.8 |

| Pregunta | Esperado | Modo A | Modo B | Herramientas en modo B |
|---|---:|---:|---:|---|
| Producción de oro 2024 (t) | 105.44 | no sabe | 105.44 ✔ | `serie` |
| Exportación de oro 2024 (t) | 202.6 | no sabe | 202.6 ✔ | `serie` (corrige la unidad miles/millones) |
| Oro de Madre de Dios 2024 (t) | 1.09 | no sabe | 1.09 ✔ | `oro_por_departamento`, `buscar_series`, `serie` |
| Variación del oro 2015-2024 (%) | −25.9 | no sabe | −25.90 ✔ | `resumen` |
| Pobreza nacional 2024 (%) | 27.6 | 27.6 ✔ | 27.6 ✔ | ninguna (memoria) |
| Pobreza rural 2024 (%) | 39.3 | no sabe | 39.4 ✔ | Bash sobre `personas_2024.parquet` |
| Pobreza Puno 2024 (%) | 39.9 | no sabe | 39.9 ✔ | Bash sobre la salida de la Skill |
| Pobreza nacional 2020 (%) | 30.1 | 30.1 ✔ | 30.1 ✔ | ninguna (memoria) |
| Mixta: dpto. con más oro 2024 → pobreza | La Libertad, 30.2 | no sabe | La Libertad, 30.2 ✔ | `oro_por_departamento` + Bash |
| Mixta: mayor caída de oro en B → pobreza | Madre de Dios, 11.1 | no sabe | Madre de Dios, 11.1 ✔ | `oro_por_departamento` + Bash |

**Mejoraron:** 8 preguntas (las 4 del BCRP, 2 de ENAHO y las 2 mixtas). **Empeoraron:** ninguna.

## Principales errores y observaciones

1. **El modo A no inventa: se abstiene.** Ante la instrucción de no estimar, devolvió `null` en 8 de 10 preguntas.
   Solo respondió las dos cifras nacionales de pobreza más difundidas (27.6 % y 30.1 %). En la mixta del oro mencionó
   La Libertad como «departamento probable», pero no dio la cifra. Sin herramientas, el problema no son las cifras
   falsas: es que no hay respuesta.
2. **En el modo B, dos aciertos de ENAHO no usaron herramientas.** La pobreza nacional de 2024 y la de 2020 las
   respondió de memoria, igual que el modo A. Ahí MCP y Skills no aportaron nada.
3. **Pobreza rural con otro método.** El modo B calculó 39.4 % con la base de personas (`facpob07`). El INEI publica
   39.3 % con `factor07 × mieperho`. Está dentro de la tolerancia (±0.2), pero muestra que el agente no siempre elige
   el método oficial que indica la Skill.
4. **Las Skills no se invocaron con la herramienta `Skill`.** En las preguntas cortas el modelo fue directo a las
   salidas que las Skills ya habían dejado en `salidas/` (con Bash, Glob y Read). Las Skills sí se activaron
   formalmente en la ejecución integrada (`evidencias_ia/integracion/`), que es donde hacía falta procesar datos.
5. **Primera corrida del modo B descartada (fuga de respuestas).** En una corrida previa, el modo B corría en la carpeta
   real del proyecto, y en la pregunta de pobreza rural leyó la respuesta esperada en `evaluacion/preguntas.csv`.
   Esa corrida se guardó en `resultados_modoB_descartado.csv` y no se cuenta. El modo B se repitió en una copia del
   proyecto sin `evaluacion/` ni `evidencias_ia/`.
6. **Costo en tiempo.** El modo B tarda unas 8 veces más (52 s frente a 6 s en promedio). Las preguntas del BCRP
   llegaron a 90-130 s porque tres consultas corrían en paralelo contra la API, que limita los pedidos seguidos.

## Conclusión

Con el MCP y las Skills, el agente pasó de **2 a 10 respuestas correctas**. Cada cifra del BCRP salió con su código
de serie y su periodo, y las cifras de ENAHO salieron de bases ponderadas y validadas. La mejora se debe a que el
agente tiene acceso a los datos, no a un mejor razonamiento: sin herramientas, el modelo se abstuvo en vez de
inventar. La ganancia es mayor en las preguntas del BCRP y en las mixtas, que exigen cruzar dos fuentes (0/6 → 6/6).
El precio es más tiempo de respuesta. Con 10 preguntas y una sola corrida por modo, esta es una comparación
ilustrativa, no una estimación estadística del desempeño.
