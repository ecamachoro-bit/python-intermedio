---
name: graficando-enaho
description: Hace gráficos de la pobreza monetaria o extrema de la ENAHO del INEI por área urbana y rural, sexo, grupo de edad, departamento o grupo minero, y la evolución 2015-2024 por grupo minero junto a la brecha del oro del BCRP, con reglas fijas. Úsala cuando pidan graficar, comparar o visualizar la pobreza del Perú con la ENAHO, o su evolución en departamentos mineros.
argument-hint: [area|sexo|edad|departamento|grupo_minero|serie]
---

# Graficar la ENAHO

1. Si no existe `salidas/hogares_2024.parquet` (o, para la serie, `salidas/pobreza_grupo_minero_2015_2024.csv`),
   usa primero la skill `limpiando-enaho`.
2. Elige según el pedido. Si llamaron la skill con argumento, úsalo como `--por $0`:
   - Barras de un año: `uv run ${CLAUDE_SKILL_DIR}/scripts/graficar.py --por <area|sexo|edad|departamento|grupo_minero>`
     (agrega `--indicador pobre_extremo` para pobreza extrema).
   - Evolución 2015-2024 por grupo minero: `uv run ${CLAUDE_SKILL_DIR}/scripts/serie_grupos.py`.
     Si existe `salidas/brecha_oro_2015_2024.json` (respuesta de la herramienta MCP `brecha_oro`), agrega
     `--brecha salidas/brecha_oro_2015_2024.json` para el gráfico de dos paneles BCRP + ENAHO.
3. Muestra la ruta del PNG y las cifras que imprime el script; no inventes otras.

## Reglas fijas (ya están en los scripts)

- Pondera siempre: área, departamento y grupo con `factor07 × mieperho`; sexo y edad con `facpob07`.
- Barras desde cero, ordenadas, un solo color y el valor escrito en cada barra.
- Líneas: un color fijo por grupo (A azul, B naranja, C verde, D amarillo, Perú gris discontinuo), etiqueta directa
  al final de cada línea, eje y desde cero. Nunca dos ejes y en el mismo panel: BCRP y ENAHO van en paneles separados.
- El título dice qué, dónde y cuándo; nota al pie con la fuente (INEI, ENAHO; BCRP con códigos de serie).
- PNG a 200 dpi en `figuras/`.
