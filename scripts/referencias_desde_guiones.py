"""Genera el borrador de la transcripción de referencia de cada clip a partir de los guiones.

Es un borrador: la referencia final es la que la autora corrige escuchando cada grabación
(ver scripts/revisar_referencias.py), porque al grabar nadie lee el guion palabra por palabra.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from motor import cargar_config  # noqa: E402

cfg = cargar_config()
raiz = Path(__file__).resolve().parent.parent
destino = raiz / cfg["rutas"]["verdad"] / "referencias"
destino.mkdir(parents=True, exist_ok=True)

for archivo in ("entrevistas.md", "llamadas.md"):
    texto = (raiz / cfg["rutas"]["guiones"] / archivo).read_text(encoding="utf-8")
    for bloque in re.split(r"\n## ", texto)[1:]:
        clip = re.match(r"([EL]\d\d)", bloque)
        if not clip:
            continue
        turnos = re.findall(r"^\*\*[AB]:\*\*\s*(.+)$", bloque, re.M)
        salida = destino / f"{clip.group(1)}.txt"
        if salida.exists() and "--forzar" not in sys.argv:
            print(f"{salida.name}: ya existe (revisado a mano); no se sobrescribe")
            continue
        salida.write_text("\n".join(turnos) + "\n", encoding="utf-8")
        print(f"{salida.name}: {len(turnos)} turnos")
