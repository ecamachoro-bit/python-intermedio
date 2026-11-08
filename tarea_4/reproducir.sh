#!/usr/bin/env bash
# Reproduce todo el procesamiento de la Tarea 4 desde los zip de datos/ (ver README, sección 5).
set -euo pipefail
export PYTHONUTF8=1
SK=.claude/skills
uv run pytest -q                                                     # 1. MCP: 10 pruebas
uv run $SK/limpiando-enaho/scripts/limpiar.py --anio 2024            # 2. ENAHO 2024 completa + validacion.txt
for a in 2015 2016 2017 2018 2019 2020 2021 2022 2023; do
  uv run $SK/limpiando-enaho/scripts/limpiar.py --anio $a --solo-sumaria > /dev/null
done
uv run $SK/limpiando-enaho/scripts/serie_pobreza.py                 # 3. serie por departamento y grupo
uv run $SK/limpiando-enaho/scripts/empleo_minero.py > /dev/null     # 4. empleo minero (módulo 05)
uv run scripts/consultar_bcrp.py                                     # 5. BCRP vía MCP -> salidas/*.json
uv run scripts/graficar_oro_bcrp.py > /dev/null                      # 6. figuras y mapas
for g in area sexo departamento grupo_minero; do uv run $SK/graficando-enaho/scripts/graficar.py --por $g > /dev/null; done
uv run $SK/graficando-enaho/scripts/serie_grupos.py --brecha salidas/brecha_oro_2015_2024.json > /dev/null
uv run $SK/mapeando-enaho/scripts/mapear.py > /dev/null
uv run $SK/mapeando-enaho/scripts/mapear.py --marcar-grupos
uv run scripts/indicadores.py                                        # 7. tabla final de indicadores
