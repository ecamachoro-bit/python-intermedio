"""Seudonimización por clip, con un diccionario armado tras revisión humana de las 28 transcripciones.

Criterio: se reemplazan personas privadas (entrevistados, entrevistadores, personas mencionadas) por
[PERSONA_nn]. Se conservan figuras públicas, instituciones y lugares. Se aplica por clip para no tocar palabras
comunes (p. ej. "luz"). Se usa igual en las transcripciones automáticas, en las referencias manuales y en
todos los modelos comparados.

El diccionario con los nombres originales está en datos/raw/seudonimos_privado.json, que NO se versiona:
publicarlo revelaría justamente los nombres que se quieren proteger.
"""
import json
from functools import lru_cache
from pathlib import Path

from voz import seudonimizar

PRIVADO = Path(__file__).resolve().parent / "datos" / "raw" / "seudonimos_privado.json"


@lru_cache(maxsize=1)
def reemplazos() -> dict[str, dict[str, str]]:
    return json.loads(PRIVADO.read_text(encoding="utf-8"))


def aplicar(cid: str, texto: str) -> str:
    rep = reemplazos().get(cid)
    return seudonimizar(texto, rep) if rep and isinstance(texto, str) else texto


def resumen():
    """Cuántos nombres se reemplazan en cada clip y con qué seudónimos (sin mostrar los originales)."""
    return {cid: sorted(set(rep.values())) for cid, rep in reemplazos().items()}
