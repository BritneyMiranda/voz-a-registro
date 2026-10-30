"""Puerta de calidad: falla (exit 1) si las métricas recalculadas desde la caché bajan del umbral.

Corre en GitHub Actions, donde no hay GPU: por eso evalúa transcripciones guardadas y nunca transcribe.
Si un cambio en las reglas o en la normalización empeora el registro, el pull request queda en rojo.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from motor import cargar_config  # noqa: E402

cfg = cargar_config()
q = cfg["calidad"]
resumen = json.loads((RAIZ / cfg["rutas"]["resultados"] / "resumen.json").read_text(encoding="utf-8"))
nombres = {t["corrida"] for t in resumen["transcripcion"]}
corrida = q["corrida"] if q["corrida"] in nombres else q["corrida_respaldo"]

fallas = []
wer = next(t["wer"] for t in resumen["transcripcion"] if t["corrida"] == corrida)
if wer > q["wer_maximo"]:
    fallas.append(f"WER {wer:.3f} > {q['wer_maximo']}")
for tarea in ("entrevista", "pedido"):
    filas = [r for r in resumen["registro"] if r["corrida"] == corrida and r["metodo"] == "reglas" and r["tarea"] == tarea]
    exactitud = sum(r["exactitud"] * r["n"] for r in filas) / sum(r["n"] for r in filas)
    print(f"{tarea}: exactitud de campos {exactitud:.2f}")
    if exactitud < q[f"exactitud_minima_{tarea}"]:
        fallas.append(f"exactitud {tarea} {exactitud:.2f} < {q[f'exactitud_minima_{tarea}']}")
val = next((v for v in resumen["validacion"] if v["corrida"] == corrida and v["metodo"] == "reglas"), None)
if val is None or val["atrapados"] < q["errores_plantados_atrapados_min"]:
    fallas.append(f"el validador atrapó {val and val['atrapados']} de {val and val['errores_plantados']} errores plantados")

print(f"corrida evaluada: {corrida} · WER {wer:.3f}")
if fallas:
    print("PUERTA CERRADA:\n  " + "\n  ".join(fallas))
    sys.exit(1)
print("PUERTA ABIERTA: la calidad se mantiene")
