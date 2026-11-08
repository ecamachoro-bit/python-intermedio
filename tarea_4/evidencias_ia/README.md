# Evidencias del uso de IA

Todo el proyecto se desarrolló con **Claude Code** (Opus) en una sola conversación con la estudiante, más dos tipos
de ejecuciones no interactivas (`claude -p`) que también son evidencia. Se ocultaron correos y tokens.

| Carpeta / archivo | Qué contiene |
|---|---|
| [`conversacion_desarrollo.md`](conversacion_desarrollo.md) | **Conversación completa** de desarrollo (exportada del historial de Claude Code con `scripts/exportar_conversacion.py`): lectura del enunciado, definición de los grupos mineros con la estudiante, servidor MCP, Skills, integración, evaluación, errores y correcciones |
| [`mcp/pruebas.txt`](mcp/pruebas.txt) | `pytest -v`: 10 passed (8 originales + 2 propias) |
| [`skills/coordinacion_skills.md`](skills/coordinacion_skills.md) | **Coordinación de Skills:** en una copia del proyecto sin `salidas/`, el pedido «Haz un mapa de la pobreza monetaria por departamento con ENAHO 2024» activó `mapeando-enaho`, que detectó la falta de la base, ejecutó `limpiando-enaho` (validación OK) y luego hizo el mapa (25/25) |
| [`skills/`](skills/) | Validaciones de la Skill de limpieza (2024 y 2015-2023) y comparación del mapa con la referencia de la Sesión 16 (25/25) |
| [`integracion/prompt_agente.md`](integracion/prompt_agente.md) | Pedido dado al agente para la ejecución integrada |
| [`integracion/ejecucion_agente.jsonl`](integracion/ejecucion_agente.jsonl) | Registro completo (stream-json) de esa ejecución: 4 herramientas MCP + 3 Skills en una misma sesión |
| [`integracion/ejecucion_agente.md`](integracion/ejecucion_agente.md) | El mismo registro en Markdown legible |
| [`integracion/herramientas_usadas.txt`](integracion/herramientas_usadas.txt) | Conteo de herramientas usadas por el agente |
| [`evaluacion/`](evaluacion/) | Registro de las 30 llamadas `claude -p` de la evaluación (modo A, modo B descartado y modo B final) |

Correcciones hechas durante el desarrollo (todas visibles en la conversación): factor de expansión en `float32`
→ `float64`; doble redondeo de CSV; `serie_pobreza.py` redondeaba antes de restar (lo detectó el propio agente en
la ejecución integrada); orden de series de la API del BCRP en la verificación independiente; fuga de respuestas
esperadas en la primera corrida del modo B (se descartó y se repitió en una copia aislada del proyecto).
