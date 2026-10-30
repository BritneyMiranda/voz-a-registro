"""Escribe las tablas de resultados del README desde resultados/resumen.json (entre marcadores).

Así ningún número del README está escrito a mano: si cambian la caché o la referencia, se regeneran.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from motor import cargar_config  # noqa: E402

cfg = cargar_config()
res = json.loads((RAIZ / cfg["rutas"]["resultados"] / "resumen.json").read_text(encoding="utf-8"))


def ic(x):
    return f"[{x[0]:.3f}, {x[1]:.3f}]"


def md(df):
    cab = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns)
    return cab + "\n" + "\n".join("| " + " | ".join(str(v) for v in fila) + " |" for fila in df.itertuples(index=False))


t = pd.DataFrame(res["transcripcion"])
transcripcion = md(pd.DataFrame({
    "Corrida": t.corrida, "Clips": t.clips, "WER": t.wer.map("{:.3f}".format), "IC 95 %": t.wer_ic95.map(ic),
    "CER": t.cer.map("{:.3f}".format), "s / min de audio": t.segundos_por_minuto.map("{:.1f}".format),
    "VRAM pico (MB)": t.vram_total_usada_mb.map(lambda v: "—" if pd.isna(v) else f"{v:.0f}"),
    "Dispositivo (leído)": t.dispositivo, "GPU": t.gpu.fillna("—")}))

cambios = md(pd.DataFrame([{"A": c["a"], "B": c["b"], "Clips": c["clips"],
                            "Clips con texto distinto": len(c["clips_con_texto_distinto"]),
                            "WER entre A y B": f"{c['wer_entre_ellas']:.3f}"} for c in res["comparaciones_texto"]])) \
    if res["comparaciones_texto"] else "_Pendiente: requiere las corridas de Colab._"

glosario = md(pd.DataFrame([{"Sin glosario": g["sin_glosario"], "Con glosario": g["con_glosario"], "Clips": g["clips"],
                             "Δ WER (con − sin)": f"{g['dif_wer']:+.3f}", "IC 95 % (bootstrap pareado)": ic(g["dif_wer_ic95"])}
                            for g in res["glosario"]])) if res["glosario"] else "_Pendiente: requiere las corridas de Colab._"

r = pd.DataFrame(res["registro"])
r0 = r[r.corrida.str.startswith("L0") & ~r.corrida.str.contains("small|glosario-(?:hotwords|initial_prompt)|colab")]
filas = []
for (corrida, tarea, campo), g in r0.groupby(["corrida", "tarea", "campo"]):
    fila = {"Corrida": corrida, "Tarea": tarea, "Campo": campo}
    for _, x in g.iterrows():
        fila[f"Exactitud {x.metodo}"] = f"{x.exactitud:.2f} [{x.ic95[0]:.2f}, {x.ic95[1]:.2f}]"
        fila[f"Verificados {x.metodo}"] = f"{x.verificados:.2f}"
        if x.error_abs_medio is not None and not pd.isna(x.error_abs_medio):
            fila[f"Error abs. {x.metodo}"] = f"{x.error_abs_medio:.1f}"
    filas.append(fila)
registro = md(pd.DataFrame(filas).fillna("—"))
macro = md(pd.DataFrame(res["macro_f1"]).round(3)) if res["macro_f1"] else ""

v = pd.DataFrame(res["validacion"])
validacion = md(v) if len(v) else "_Pendiente._"

BASE = "large-v3-turbo_float16_cuda_glosario-ninguno"
esc = r[r.corrida.str.endswith(BASE)].assign(nivel=lambda d: d.corrida.str[:2])
if len(esc):
    por_clip = pd.read_csv(RAIZ / cfg["rutas"]["resultados"] / "transcripcion_por_clip.csv")
    w = por_clip[por_clip.corrida.str.endswith(BASE)].assign(nivel=lambda d: d.corrida.str[:2])
    wer = w.groupby(["nivel", "tarea"]).wer.mean().unstack().add_prefix("WER ")
    exact = esc.groupby(["nivel", "tarea", "metodo"]).apply(lambda g: (g.exactitud * g.n).sum() / g.n.sum())
    exact = exact.unstack(["tarea", "metodo"])
    exact.columns = [f"campos {t} ({m})" for t, m in exact.columns]
    escalera = md(wer.join(exact).round(3).reset_index())
else:
    escalera = "_Pendiente: requiere las corridas L1–L3 de Colab._"

bloques = {"TRANSCRIPCION": transcripcion, "CAMBIOS": cambios, "GLOSARIO": glosario, "REGISTRO": registro + "\n\n" + macro,
           "ESCALERA": escalera, "VALIDACION": validacion}
readme = (RAIZ / "README.md").read_text(encoding="utf-8")
for nombre, contenido in bloques.items():
    readme = re.sub(rf"(<!-- {nombre} -->).*?(<!-- /{nombre} -->)", lambda m: f"{m.group(1)}\n{contenido}\n{m.group(2)}",
                    readme, flags=re.S)
(RAIZ / "README.md").write_text(readme, encoding="utf-8")
print("tablas del README actualizadas")
