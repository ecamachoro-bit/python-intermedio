"""¿Mejoran MCP y Skills las respuestas? Las mismas 10 preguntas en dos modos, contra la cifra oficial.

    uv run evaluacion/evaluar.py                       # ambos modos, con Sonnet
    uv run evaluacion/evaluar.py --modos sin --modelo sonnet

Basado en evaluar.py de la Sesión 04. Cada pregunta va a Claude Code en modo no interactivo (claude -p), en una
sesión independiente (--no-session-persistence), con la misma instrucción y el mismo modelo.

Modo A "sin":  sin MCP (--strict-mcp-config sin config), sin Skills (--disallowedTools Skill), sin herramientas
               (--tools ""), y ejecutado en una carpeta temporal vacía fuera del proyecto, para que no pueda leer
               salidas/ ni .claude/skills/. Responde solo con su conocimiento.
Modo B "con":  con el MCP del BCRP (.mcp.json) y las Skills del proyecto, con Bash, Read, Glob y Grep para ejecutar
               los scripts de las Skills. Corre en una COPIA del proyecto sin evaluacion/ ni evidencias_ia/, para que
               no pueda leer las respuestas esperadas (en una primera corrida leyó preguntas.csv: ver
               resultados_modoB_descartado.csv y comparacion.md).

Calificación (tolerancia fijada en preguntas.csv antes de correr): "acierta" si |valor − verdad| <= tolerancia;
en las preguntas mixtas además debe identificar el departamento correcto (exactitud del dato + coherencia).
"no sabe" si devuelve null. Escribe evaluacion/resultados.csv.
"""
import argparse
import json
import subprocess
import tempfile
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

AQUI = Path(__file__).resolve().parent
PROYECTO = AQUI.parent
ESQUEMA = {"type": "object", "required": ["valor", "fuente"],
           "properties": {"valor": {"type": ["number", "null"]}, "unidad": {"type": "string"},
                          "departamento": {"type": "string"}, "fuente": {"type": "string"}}}
INSTRUCCION = ("Responde con un solo número en «valor», en la unidad que pide la pregunta. Si la pregunta pide "
               "identificar un departamento, escríbelo en «departamento». Si no puedes saberlo con certeza, pon "
               "valor null: no estimes. En «fuente» di de dónde sale la cifra (serie, base o cálculo).\n\n")
VACIA = Path(tempfile.gettempdir()) / "tarea4_modo_sin"
COPIA = Path(tempfile.gettempdir()) / "tarea4_modo_con"
EXCLUIR = {"evaluacion", "evidencias_ia", ".venv", "__pycache__", ".pytest_cache"}


def preparar_copia():
    """Copia el proyecto sin las carpetas que contienen respuestas esperadas."""
    import shutil
    if COPIA.exists():
        shutil.rmtree(COPIA)
    shutil.copytree(PROYECTO, COPIA, ignore=lambda d, nombres: [n for n in nombres if n in EXCLUIR])
    assert not (COPIA / "evaluacion").exists()
MODOS = {
    "sin": {"cwd": VACIA, "args": ["--tools", "", "--strict-mcp-config", "--disallowedTools", "Skill"]},
    "con": {"cwd": COPIA, "args": ["--strict-mcp-config", "--mcp-config", str(COPIA / ".mcp.json"),
                                      "--tools", "Bash,Read,Glob,Grep,Skill",
                                      "--allowedTools", "Bash,Read,Glob,Grep,Skill,mcp__bcrp"]},
}


def _norm(s):
    return unicodedata.normalize("NFD", str(s or "").lower()).encode("ascii", "ignore").decode()


def preguntar(pregunta, modo, modelo):
    cmd = ["claude", "-p", INSTRUCCION + pregunta, "--output-format", "stream-json", "--verbose",
           "--json-schema", json.dumps(ESQUEMA), "--no-session-persistence", "--model", modelo, *MODOS[modo]["args"]]
    t = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=900,
                              cwd=MODOS[modo]["cwd"])
        salida = proc.stdout
    except subprocess.TimeoutExpired:
        salida = ""
    herramientas, final = [], {}
    for linea in salida.splitlines():
        try:
            ev = json.loads(linea)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if b.get("type") == "tool_use":
                    nombre = b["name"]
                    if nombre == "Skill":
                        nombre += ":" + str(b.get("input", {}).get("skill", b.get("input", {}).get("command", "")))
                    herramientas.append(nombre)
        if ev.get("type") == "result":
            final = ev
    r = final.get("structured_output") or {}
    return {"valor": r.get("valor"), "departamento": r.get("departamento", ""),
            "fuente_respuesta": r.get("fuente", final.get("result", "")[:300]),
            "herramientas": ";".join(dict.fromkeys(herramientas)), "n_llamadas": len(herramientas),
            "segundos": round(time.time() - t, 1), "turnos": final.get("num_turns"),
            "error": "" if final and not final.get("is_error") else (final.get("result", "sin respuesta")[:200]
                                                                     if final else "sin respuesta / timeout")}


def calificar(fila, q):
    if fila["valor"] is None:
        return "no sabe"
    ok = abs(float(fila["valor"]) - q.verdad) <= q.tolerancia
    if isinstance(q.departamento_esperado, str) and q.departamento_esperado:
        ok = ok and _norm(q.departamento_esperado) in _norm(fila["departamento"]) + " " + _norm(fila["fuente_respuesta"])
    return "acierta" if ok else "se equivoca"


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--modos", nargs="+", default=["sin", "con"], choices=list(MODOS))
    p.add_argument("--modelo", default="sonnet")
    p.add_argument("--paralelo", type=int, default=4)
    a = p.parse_args()
    VACIA.mkdir(exist_ok=True)
    if "con" in a.modos:
        preparar_copia()
    preguntas = pd.read_csv(AQUI / "preguntas.csv")
    casos = [(q, m) for m in a.modos for q in preguntas.itertuples()]
    print(f"{len(casos)} llamadas a claude -p con {a.modelo}...")
    with ThreadPoolExecutor(a.paralelo) as ex:
        respuestas = list(ex.map(lambda c: preguntar(c[0].pregunta, c[1], a.modelo), casos))

    filas = []
    for (q, m), r in zip(casos, respuestas):
        filas.append({"id": q.id, "tipo": q.tipo, "modo": m, "modelo": a.modelo, "pregunta": q.pregunta,
                      "verdad": q.verdad, "tolerancia": q.tolerancia, "departamento_esperado": q.departamento_esperado,
                      **r, "resultado": calificar(r, q)})
    res = pd.DataFrame(filas)
    previo = AQUI / "resultados.csv"
    if previo.exists() and set(a.modos) != set(MODOS):
        res = pd.concat([pd.read_csv(previo).query("modo not in @a.modos"), res])
    res.to_csv(previo, index=False, encoding="utf-8")

    print("\n" + res.pivot(index="id", columns="modo", values="valor").to_string())
    tabla = res.groupby("modo").resultado.value_counts().unstack(fill_value=0)
    tabla["segundos_promedio"] = res.groupby("modo").segundos.mean().round(1)
    print("\n" + tabla.to_string())
