"""Guarda en salidas/ las respuestas de las herramientas MCP del BCRP usadas en el informe.

Llama al servidor MCP (mcp/server.py) con un cliente FastMCP, igual que Claude Code, para que cualquiera
pueda reproducir las cifras sin abrir Claude Code:

    uv run scripts/consultar_bcrp.py

Sale: salidas/brecha_oro_2015_2024.json, salidas/oro_por_departamento_2015_2024.json,
      salidas/comparar_produccion_oro.json, salidas/comparar_exportacion_oro.json
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp"))
sys.stdout.reconfigure(encoding="utf-8")
from fastmcp import Client  # noqa: E402
from server import mcp  # noqa: E402

SALIDAS = Path("salidas")
PEDIDOS = {
    "brecha_oro_2015_2024": ("brecha_oro", {"anio_inicio": 2015, "anio_fin": 2024}),
    "oro_por_departamento_2015_2024": ("oro_por_departamento", {"anio_inicio": 2015, "anio_fin": 2024}),
    "comparar_produccion_oro": ("comparar_periodos", {"codigo": "RD15543DA", "desde_a": "2015", "hasta_a": "2019",
                                                      "desde_b": "2020", "hasta_b": "2024"}),
    "comparar_exportacion_oro": ("comparar_periodos", {"codigo": "PM40098BA", "desde_a": "2015", "hasta_a": "2019",
                                                       "desde_b": "2020", "hasta_b": "2024"}),
}


async def main():
    SALIDAS.mkdir(exist_ok=True)
    async with Client(mcp) as c:
        for nombre, (herramienta, args) in PEDIDOS.items():
            r = (await c.call_tool(herramienta, args)).data
            (SALIDAS / f"{nombre}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{herramienta}({args}) -> salidas/{nombre}.json")


if __name__ == "__main__":
    asyncio.run(main())
