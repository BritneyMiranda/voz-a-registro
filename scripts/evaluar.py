"""Calcula todas las métricas leyendo SOLO la caché (no transcribe nada; corre sin GPU).

Entradas:  cache/transcripciones/<corrida>/<clip>.json   (scripts/transcribir_corpus.py o el notebook de Colab)
           cache/extracciones_llm/<corrida>/<clip>.json  (notebook de Colab, opcional)
           verdad/referencias/*.txt, verdad/entrevistas.json, verdad/llamadas.json
Salidas:   resultados/*.csv y resultados/resumen.json (los lee la app y la puerta de calidad de CI)
"""
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from motor import cargar_config  # noqa: E402
from motor.extraccion_llm import a_registro  # noqa: E402
from motor.extraccion_reglas import extraer_entrevista, extraer_pedido  # noqa: E402
from motor.metricas import (bootstrap, comparar_entrevista, comparar_pedido, macro_f1,  # noqa: E402
                            wer_cer, wilson)
from motor.validacion import validar  # noqa: E402
from motor.verificacion import VERIFICADO, verificar  # noqa: E402

cfg = cargar_config()
R = cfg["rutas"]
cache, salida = RAIZ / R["cache"], RAIZ / R["resultados"]
salida.mkdir(exist_ok=True)
B = cfg["metricas"]["bootstrap_repeticiones"]
verdad_e = json.loads((RAIZ / R["verdad"] / "entrevistas.json").read_text(encoding="utf-8"))["clips"]
verdad_l = json.loads((RAIZ / R["verdad"] / "llamadas.json").read_text(encoding="utf-8"))["clips"]
referencias = {p.stem: p.read_text(encoding="utf-8") for p in (RAIZ / R["verdad"] / "referencias").glob("*.txt")}


def leer_corridas(carpeta):
    corridas = {}
    for d in sorted((cache / carpeta).glob("*")) if (cache / carpeta).exists() else []:
        corridas[d.name] = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in d.glob("*.json")}
    return corridas


transcripciones = leer_corridas("transcripciones")
extracciones_llm = leer_corridas("extracciones_llm")

# ------------------------------------------------------------------ capa 1: transcripción
filas = []
for corrida, clips in transcripciones.items():
    for clip, r in clips.items():
        if clip not in referencias:
            continue
        filas.append({"corrida": corrida, "clip": clip, "tarea": "entrevista" if clip[0] == "E" else "pedido",
                      **wer_cer(referencias[clip], r["texto"]),
                      "dispositivo": r["dispositivo"], "precision": r["precision"], "gpu": r.get("gpu"),
                      "segundos_por_minuto": r["segundos_por_minuto"], "vram_pico_mb": r["vram_pico_mb"],
                      "vram_total_usada_mb": r.get("vram_total_usada_mb")})
asr_df = pd.DataFrame(filas)
asr_df.to_csv(salida / "transcripcion_por_clip.csv", index=False)

resumen_asr = []
for corrida, g in asr_df.groupby("corrida"):
    m, lo, hi = bootstrap(g["wer"], B)
    resumen_asr.append({"corrida": corrida, "clips": len(g), "wer": m, "wer_ic95": [lo, hi], "cer": g["cer"].mean(),
                        "segundos_por_minuto": g["segundos_por_minuto"].mean(),
                        "vram_pico_mb": g["vram_pico_mb"].max(), "vram_total_usada_mb": g["vram_total_usada_mb"].max(),
                        "dispositivo": ",".join(sorted(set(g["dispositivo"]))), "gpu": g["gpu"].dropna().iloc[0]
                        if g["gpu"].notna().any() else None})
pd.DataFrame(resumen_asr).to_csv(salida / "transcripcion_resumen.csv", index=False)


# ¿cambió el texto entre dos corridas? (CPU vs GPU, float16 vs int8)
def cambio_texto(a, b):
    if a not in transcripciones or b not in transcripciones:
        return None
    comunes = sorted(set(transcripciones[a]) & set(transcripciones[b]))
    distintos = [c for c in comunes
                 if wer_cer(transcripciones[a][c]["texto"], transcripciones[b][c]["texto"])["wer"] > 0]
    wer_entre = [wer_cer(transcripciones[a][c]["texto"], transcripciones[b][c]["texto"])["wer"] for c in comunes]
    return {"a": a, "b": b, "clips": len(comunes), "clips_con_texto_distinto": distintos,
            "wer_entre_ellas": sum(wer_entre) / len(wer_entre) if wer_entre else None}


comparaciones = []
nombres = list(transcripciones)
for i, a in enumerate(nombres):
    for b in nombres[i + 1:]:
        pa, pb = a.split("_"), b.split("_")
        if pa[0] == pb[0] and sum(x != y for x, y in zip(pa, pb)) == 1:   # difieren en una sola cosa
            comparaciones.append(cambio_texto(a, b))

# glosario: diferencia pareada de WER por clip, con IC bootstrap
glosario = []
for a in nombres:
    if a.endswith("glosario-ninguno"):
        for modo in ("hotwords", "initial_prompt"):
            b = a.replace("glosario-ninguno", f"glosario-{modo}")
            if b in transcripciones:
                g = asr_df[asr_df.corrida.isin([a, b])].pivot(index="clip", columns="corrida", values="wer").dropna()
                m, lo, hi = bootstrap(g[b] - g[a], B)
                glosario.append({"sin_glosario": a, "con_glosario": b, "clips": len(g),
                                 "dif_wer": m, "dif_wer_ic95": [lo, hi]})

# ------------------------------------------------------------------ capa 2: registro
reg_filas, val_filas = [], []


def evaluar_registro(corrida, clip, campos, evid, texto, metodo, palabras):
    esquema = "entrevista" if clip[0] == "E" else "pedido"
    ver = verificar(campos, evid, texto, esquema, cfg)
    if esquema == "entrevista":
        comp = comparar_entrevista(campos, verdad_e[clip])
    else:
        comp = comparar_pedido(campos, verdad_l[clip], cfg)
    for campo, c in comp.items():
        reg_filas.append({"corrida": corrida, "metodo": metodo, "clip": clip, "tarea": esquema, "campo": campo,
                          "correcto": c["correcto"], "error_abs": c.get("error_abs"),
                          "verificado": ver.get(campo) == VERIFICADO,
                          "valor": json.dumps(campos.get(campo), ensure_ascii=False)})
    if esquema == "pedido":
        v, verdad = validar(campos, cfg, palabras), verdad_l[clip]
        planta_error = verdad["trampas"]["total_erroneo"]
        registro_igual = comp["items"]["correcto"] and comp["promocion"]["correcto"] and comp["total_dicho"]["correcto"]
        if v["estado"] == "no_cuadra":
            causa_real = "error_hablante" if (planta_error and registro_igual) else "posible_error_asr"
        else:
            causa_real = None
        val_filas.append({"corrida": corrida, "metodo": metodo, "clip": clip, "total_erroneo_plantado": planta_error,
                          "registro_igual_a_verdad": registro_igual, "estado": v["estado"],
                          "total_calculado": v.get("total_calculado"), "total_dicho": v.get("total_dicho"),
                          "diagnostico": v.get("diagnostico"), "motivo": v.get("motivo"), "causa_real": causa_real,
                          "diagnostico_correcto": None if causa_real is None else v.get("diagnostico") == causa_real})


for corrida, clips in transcripciones.items():
    for clip, r in clips.items():
        if clip not in verdad_e and clip not in verdad_l:
            continue
        f = extraer_entrevista if clip[0] == "E" else extraer_pedido
        campos, evid = f(r["texto"], cfg)
        evaluar_registro(corrida, clip, campos, evid, r["texto"], "reglas", r.get("palabras"))
for corrida, clips in extracciones_llm.items():
    for clip, x in clips.items():
        esquema = "entrevista" if clip[0] == "E" else "pedido"
        campos, evid = a_registro(x["respuesta"], esquema, cfg)
        palabras = transcripciones.get(corrida, {}).get(clip, {}).get("palabras")
        evaluar_registro(corrida, clip, campos, evid, x["texto"], "llm", palabras)

reg = pd.DataFrame(reg_filas)
reg.to_csv(salida / "registro_por_campo.csv", index=False)
val = pd.DataFrame(val_filas)
val.to_csv(salida / "validacion.csv", index=False)

resumen_reg = []
for (corrida, metodo, tarea, campo), g in reg.groupby(["corrida", "metodo", "tarea", "campo"]):
    lo, hi = wilson(int(g.correcto.sum()), len(g))
    resumen_reg.append({"corrida": corrida, "metodo": metodo, "tarea": tarea, "campo": campo, "n": len(g),
                        "exactitud": g.correcto.mean(), "ic95": [lo, hi], "verificados": g.verificado.mean(),
                        "error_abs_medio": g.error_abs.dropna().mean() if g.error_abs.notna().any() else None})
macro = []
for (corrida, metodo), g in reg[reg.campo == "nivel_ingles"].groupby(["corrida", "metodo"]):
    pred = [json.loads(v) for v in g.valor]
    macro.append({"corrida": corrida, "metodo": metodo,
                  "macro_f1_ingles": macro_f1([verdad_e[c]["nivel_ingles"] for c in g["clip"]], pred)})

# atrapados vs. perdidos por nivel (solo reglas: es el camino por defecto del motor)
atrapados = []
for (corrida, metodo), g in val.groupby(["corrida", "metodo"]) if len(val) else []:
    plantados = g[g.total_erroneo_plantado]
    # roto = el total dicho está mal a propósito, o el ASR/la extracción dañó el registro
    rotos = g[g.total_erroneo_plantado | ~g.registro_igual_a_verdad]
    sanos = g[~g.total_erroneo_plantado & g.registro_igual_a_verdad]
    diag = g[g.diagnostico_correcto.notna()]
    atrapados.append({"corrida": corrida, "metodo": metodo,
                      "errores_plantados": len(plantados),
                      "atrapados": int((plantados.estado == "no_cuadra").sum()),
                      "perdidos": int((plantados.estado != "no_cuadra").sum()),
                      "registros_rotos": len(rotos),
                      "rotos_atrapados": int((rotos.estado == "no_cuadra").sum()),
                      "rotos_perdidos": int((rotos.estado != "no_cuadra").sum()),
                      "registros_sanos": len(sanos),
                      "falsas_alarmas": int((sanos.estado == "no_cuadra").sum()),
                      "diagnosticos_evaluables": len(diag),
                      "diagnosticos_correctos": int(diag.diagnostico_correcto.sum()) if len(diag) else 0})

# ¿predice el WER si el registro sirve? exactitud del registro por clip vs WER del clip
por_clip = reg[reg.metodo == "reglas"].groupby(["corrida", "clip"]).correcto.mean().rename("exactitud_registro")
wer_vs = asr_df.set_index(["corrida", "clip"])[["wer"]].join(por_clip, how="inner").reset_index()
wer_vs.to_csv(salida / "wer_vs_registro.csv", index=False)

resumen = {"transcripcion": resumen_asr, "comparaciones_texto": [c for c in comparaciones if c],
           "glosario": glosario, "registro": resumen_reg, "macro_f1": macro, "validacion": atrapados}
(salida / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1, default=float),
                                     encoding="utf-8")
print(f"{len(asr_df)} transcripciones, {len(reg)} campos evaluados, {len(val)} validaciones → {salida}")
