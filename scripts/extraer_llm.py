"""Extracción con Qwen sobre transcripciones ya guardadas en la caché (se corre en Colab, con GPU).

Guarda la respuesta cruda del modelo en cache/extracciones_llm/<corrida>/<clip>.json; evaluar.py la
convierte en registro y le aplica la misma regla de verificación que a las reglas.

    python scripts/extraer_llm.py --corridas L0_large-v3-turbo_float16_cuda_glosario-ninguno
"""
import argparse
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from motor import cargar_config  # noqa: E402
from motor.extraccion_llm import preguntar  # noqa: E402

cfg = cargar_config()
ap = argparse.ArgumentParser()
ap.add_argument("--corridas", nargs="+", required=True)
args = ap.parse_args()

cfg_llm = cfg["extraccion"]["llm"]
for corrida in args.corridas:
    origen = RAIZ / cfg["rutas"]["cache"] / "transcripciones" / corrida
    destino = RAIZ / cfg["rutas"]["cache"] / "extracciones_llm" / corrida
    destino.mkdir(parents=True, exist_ok=True)
    for p in sorted(origen.glob("*.json")):
        if (destino / p.name).exists():
            continue
        texto = json.loads(p.read_text(encoding="utf-8"))["texto"]
        esquema = "entrevista" if p.stem.startswith("E") else "pedido"
        t0 = time.perf_counter()
        respuesta = preguntar(texto, cfg_llm[f"prompt_{esquema}"], cfg_llm)
        (destino / p.name).write_text(json.dumps(
            {"clip": p.stem, "esquema": esquema, "modelo": cfg_llm["modelo"],
             "version_prompt": cfg_llm.get("version_prompt", 1), "texto": texto,
             "respuesta": respuesta, "segundos": round(time.perf_counter() - t0, 1)},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{corrida}/{p.stem}: {time.perf_counter() - t0:.0f} s", flush=True)
