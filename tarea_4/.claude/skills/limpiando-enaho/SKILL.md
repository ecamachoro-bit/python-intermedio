---
name: limpiando-enaho
description: Limpia y valida los módulos 34 (sumaria), 02 (miembros) y 05 (empleo) de la ENAHO del INEI; arma bases de personas y hogares con pobreza y factor de expansión, la serie 2015-2024 de pobreza por departamento y grupo minero, y el empleo minero e informal por departamento. Úsala cuando pidan limpiar, unir, validar o analizar la ENAHO, calcular pobreza monetaria o extrema en el Perú por departamento, área urbana o rural, sexo, edad, grupo minero o año, o el empleo en minería.
argument-hint: [año]
---

# Limpiar la ENAHO

El año es `$0`; si viene vacío, usa 2024. Todo se corre desde la raíz del proyecto (`tarea_4/`).

1. Revisa que existan los zip en `datos/` (`<código>-Modulo34.zip`, y para 2024 también `966-Modulo02.zip` y
   `966-Modulo05.zip`). Códigos INEI: 2015=498, 2016=546, 2017=603, 2018=634, 2019=687, 2020=737, 2021=759,
   2022=784, 2023=906, 2024=966. Si faltan, pide bajarlos de
   `https://proyectos.inei.gob.pe/iinei/srienaho/descarga/STATA/<código>-Modulo34.zip` (igual para 02 y 05).
2. Corre exactamente, sin reescribir la limpieza a mano:
   - 2024 completo (personas + hogares): `uv run ${CLAUDE_SKILL_DIR}/scripts/limpiar.py --anio 2024`
   - Otros años (solo hogares): `uv run ${CLAUDE_SKILL_DIR}/scripts/limpiar.py --anio <año> --solo-sumaria`
   - Serie por departamento y grupo minero (tras limpiar los 10 años):
     `uv run ${CLAUDE_SKILL_DIR}/scripts/serie_pobreza.py`
   - Empleo minero e informalidad 2024 (módulo 05): `uv run ${CLAUDE_SKILL_DIR}/scripts/empleo_minero.py`
3. Lee `salidas/validacion.txt` (o `salidas/validacion_<año>.txt`). Cada verificación dice `[PASA]` o `[FALLA]`.
   Si el RESULTADO es FALLA, el script sale con error: **detente** y muestra el reporte. Nunca ajustes cifras
   para que coincidan con la referencia.
4. Responde con las bases limpias; nunca cuentes filas ni promedies sin ponderar:
   - Departamento, área o grupo: `salidas/hogares_<año>.parquet` con `peso` (= factor07 × mieperho, método INEI).
   - Sexo o edad: `salidas/personas_2024.parquet` con `facpob07`.
   - Serie: `salidas/pobreza_departamento_2015_2024.csv` y `salidas/pobreza_grupo_minero_2015_2024.csv`.
   - Empleo minero: `salidas/empleo_minero_2024.csv` (columna `confiable` = al menos 30 mineros en la muestra).
5. Los grupos mineros (A formal de gran escala, B informal con poco oro declarado, C mixto, D resto) están en
   `referencias/grupos_mineros.csv`, con el criterio de cada departamento. Se unen por código `ccdd`, nunca por nombre.
6. Antes de usar una variable que no está en la base, lee [reference.md](reference.md).

Al responder, di la cifra con un decimal, que está ponderada y la fuente: «Fuente: INEI, ENAHO <año>».
