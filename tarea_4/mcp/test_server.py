"""El contrato del servidor: si estas pruebas pasan, Claude Code y evaluar.py pueden usarlo.

    uv run pytest -q

Llaman al servidor en memoria, igual que lo haría Claude Code, y piden datos reales al BCRP.
"""
import asyncio

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from server import mcp


async def _con_cliente(f):
    async with Client(mcp) as c:
        return await f(c)


def llamar(herramienta, **args):
    return asyncio.run(_con_cliente(lambda c: c.call_tool(herramienta, args))).data


def test_buscar_encuentra_el_ipc():
    r = llamar("buscar_series", texto="ipc 12 meses", limite=5)
    assert "PN01273PM" in [x["codigo"] for x in r]
    assert {"codigo", "nombre", "frecuencia"} <= r[0].keys()


def test_cuatro_herramientas_como_minimo():
    nombres = {t.name for t in asyncio.run(_con_cliente(lambda c: c.list_tools()))}
    assert {"buscar_series", "serie", "resumen"} <= nombres
    assert len(nombres) >= 4, "falta su herramienta propia"


def test_serie_mensual():
    r = llamar("serie", codigo="PN01271PM", desde="2025-01", hasta="2025-12")
    assert len(r["datos"]) == 12
    assert r["datos"][0]["periodo"] == "2025-01"
    assert r["datos"][2]["valor"] == pytest.approx(0.81, abs=0.01)   # IPC de Lima, marzo de 2025
    assert r["fuente"].startswith("https://estadisticas.bcrp.gob.pe")


def test_serie_diaria():
    r = llamar("serie", codigo="PD04638PD", desde="2026-10-01", hasta="2026-10-15")
    assert r["datos"][0]["periodo"] == "2026-10-01"
    assert r["datos"][-1] == {"periodo": "2026-10-15", "valor": pytest.approx(3.428, abs=0.001)}


def test_resumen_sin_cuentas_a_mano():
    r = llamar("resumen", codigo="PN01273PM", desde="2025-12", hasta="2026-09")
    assert r["primero"]["valor"] == pytest.approx(1.51, abs=0.01)
    assert r["ultimo"]["valor"] == pytest.approx(4.55, abs=0.01)
    assert r["maximo"]["periodo"] == "2026-09"
    assert {"cambio", "variacion_pct", "promedio", "minimo"} <= r.keys()


def test_codigo_inexistente_da_un_error_claro():
    with pytest.raises(ToolError, match="XX999"):
        llamar("serie", codigo="XX999", desde="2025-01", hasta="2025-02")


def test_un_recurso():
    async def contar(c):
        return len(await c.list_resources()) + len(await c.list_resource_templates())
    assert asyncio.run(_con_cliente(contar)) >= 1


def test_un_prompt():
    assert len(asyncio.run(_con_cliente(lambda c: c.list_prompts()))) >= 1


# ---------------------------------------------------------------- pruebas propias (herramienta brecha_oro)

def test_brecha_oro_calculo_y_unidades():
    """Cálculo puro con los valores oficiales 2024 de BCRPData (RD15543DA y PM40098BA)."""
    from server import calcular_brecha
    r = calcular_brecha({2024: 105437816}, {2024: 6514, 2023: None})
    assert len(r) == 1, "los años sin dato en una de las series se descartan"
    assert r[0] == {"anio": 2024, "produccion_t": 105.4, "exportacion_t": 202.6,
                    "brecha_t": 97.2, "brecha_pct": 48.0}


def test_brecha_oro_desde_el_bcrp():
    """La herramienta MCP devuelve los diez años 2015-2024 con brecha positiva y cita las dos series."""
    r = llamar("brecha_oro", anio_inicio=2015, anio_fin=2024)
    assert [f["anio"] for f in r["datos"]] == list(range(2015, 2025))
    assert all(f["exportacion_t"] > f["produccion_t"] for f in r["datos"])
    assert r["series"] == {"produccion": "RD15543DA", "exportacion": "PM40098BA"}
    with pytest.raises(ToolError, match="anio_inicio"):
        llamar("brecha_oro", anio_inicio=2024, anio_fin=2015)
