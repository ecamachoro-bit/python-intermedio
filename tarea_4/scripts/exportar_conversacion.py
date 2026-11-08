"""Convierte un historial de Claude Code (.jsonl) en Markdown legible para evidencias_ia/, ocultando datos sensibles.

    uv run scripts/exportar_conversacion.py <historial.jsonl> <salida.md> [--titulo "..."]

Incluye los mensajes del usuario, las respuestas del asistente, las llamadas a herramientas (nombre y entrada) y
un extracto de cada resultado. Oculta correos, tokens (gho_, ghp_, sk-...) y recortes de imágenes.
"""
import argparse
import json
import re
from pathlib import Path

SENSIBLE = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[correo oculto]"),
    (re.compile(r"\b(gh[opsu]_[A-Za-z0-9]{8,}|sk-[A-Za-z0-9-]{10,}|xox[bp]-[A-Za-z0-9-]+)"), "[token oculto]"),
    (re.compile(r"<system-reminder>.*?</system-reminder>", re.S), ""),
]


def limpiar(texto: str, maximo: int | None = None) -> str:
    for patron, reemplazo in SENSIBLE:
        texto = patron.sub(reemplazo, texto)
    texto = texto.strip()
    if maximo and len(texto) > maximo:
        texto = texto[:maximo] + f"\n… [recortado: {len(texto) - maximo} caracteres más]"
    return texto


def bloques(contenido):
    if isinstance(contenido, str):
        return [{"type": "text", "text": contenido}]
    return contenido or []


def main():
    p = argparse.ArgumentParser()
    p.add_argument("entrada")
    p.add_argument("salida")
    p.add_argument("--titulo", default="Conversación con Claude Code")
    a = p.parse_args()
    out = [f"# {a.titulo}", "",
           "Exportado del historial de Claude Code con `scripts/exportar_conversacion.py`. "
           "Se ocultaron correos y tokens; los resultados largos de herramientas están recortados.", ""]
    for linea in Path(a.entrada).read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(linea)
        except json.JSONDecodeError:
            continue
        tipo = ev.get("type")
        msg = ev.get("message") or {}
        hora = (ev.get("timestamp") or "")[:19].replace("T", " ")
        if tipo == "user":
            for b in bloques(msg.get("content")):
                if b.get("type") == "text":
                    t = limpiar(b["text"])
                    if t:
                        out += [f"## 👤 Usuario · {hora}", "", t, ""]
                elif b.get("type") == "tool_result":
                    c = b.get("content")
                    if isinstance(c, list):
                        c = "\n".join(x.get("text", "[imagen]") if x.get("type") == "text" else "[imagen]" for x in c)
                    t = limpiar(str(c), 1500)
                    if t:
                        out += ["<details><summary>Resultado</summary>", "", "```text", t, "```", "</details>", ""]
        elif tipo == "assistant":
            for b in bloques(msg.get("content")):
                if b.get("type") == "text" and b["text"].strip():
                    out += [f"## 🤖 Claude · {hora}", "", limpiar(b["text"]), ""]
                elif b.get("type") == "tool_use":
                    entrada = limpiar(json.dumps(b.get("input", {}), ensure_ascii=False, indent=1), 2500)
                    out += [f"**Herramienta:** `{b['name']}`", "", "```json", entrada, "```", ""]
    Path(a.salida).write_text("\n".join(out), encoding="utf-8")
    print(f"{a.salida}: {len(out)} líneas")


if __name__ == "__main__":
    main()
