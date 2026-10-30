"""Métricas de las dos capas.

Transcripción: WER y CER sobre texto normalizado con `numeros.normalizar` (números a cifras, minúsculas,
sin tildes ni puntuación), la misma regla para la referencia y para la hipótesis.
Registro: exactitud por campo, F1 macro para el inglés y error absoluto para los numéricos.
Intervalos: Wilson para proporciones; bootstrap por clip para WER y para diferencias pareadas.
"""
import math
import re

import jiwer
import numpy as np

from .numeros import normalizar


def wer_cer(referencia: str, hipotesis: str) -> dict:
    r, h = normalizar(referencia), normalizar(hipotesis)
    return {"wer": jiwer.wer(r, h), "cer": jiwer.cer(r, h)}


def wilson(aciertos: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = aciertos / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centro - margen), min(1.0, centro + margen))


def bootstrap(valores, repeticiones=2000, nivel=0.95, semilla=0):
    """IC de la media remuestreando clips (valores puede ser una diferencia pareada por clip)."""
    v = np.asarray(valores, float)
    rng = np.random.default_rng(semilla)
    medias = rng.choice(v, size=(repeticiones, len(v)), replace=True).mean(axis=1)
    a = (1 - nivel) / 2
    return float(v.mean()), float(np.quantile(medias, a)), float(np.quantile(medias, 1 - a))


def macro_f1(verdad, prediccion):
    clases = sorted(set(verdad))
    f1s = []
    for c in clases:
        tp = sum(v == c and p == c for v, p in zip(verdad, prediccion))
        fp = sum(v != c and p == c for v, p in zip(verdad, prediccion))
        fn = sum(v == c and p != c for v, p in zip(verdad, prediccion))
        f1s.append(2 * tp / (2 * tp + fp + fn) if tp else 0.0)
    return sum(f1s) / len(f1s)


def _f1_conjuntos(a, b):
    a, b = set(a), set(b)
    if not a and not b:
        return 1.0
    tp = len(a & b)
    return 2 * tp / (len(a) + len(b)) if (a or b) else 0.0


def _tokens(texto):
    return set(normalizar(texto or "").split())


def comparar_entrevista(pred: dict, verdad: dict) -> dict:
    """Devuelve, por campo, si es correcto y (para numéricos) el error absoluto."""
    r = {}
    a = pred.get("anios_experiencia")
    r["anios_experiencia"] = {"correcto": a is not None and abs(a - verdad["anios_experiencia"]) < 0.01,
                              "error_abs": None if a is None else abs(a - verdad["anios_experiencia"])}
    r["ultimo_puesto"] = {"correcto": normalizar(pred.get("ultimo_puesto") or "") == normalizar(verdad["ultimo_puesto"]),
                          "f1_tokens": _f1_conjuntos(_tokens(pred.get("ultimo_puesto")), _tokens(verdad["ultimo_puesto"]))}
    tp, tv = {normalizar(x) for x in pred.get("tecnologias") or []}, {normalizar(x) for x in verdad["tecnologias"]}
    r["tecnologias"] = {"correcto": tp == tv, "f1": _f1_conjuntos(tp, tv)}
    s, sv = pred.get("pretension_salarial"), verdad["pretension_salarial"]
    r["pretension_salarial"] = {"correcto": bool(s) and s["monto"] == sv["monto"] and s["moneda"] == sv["moneda"],
                                "error_abs": None if not s else abs(s["monto"] - sv["monto"])}
    r["disponibilidad"] = {"correcto": pred.get("disponibilidad") == verdad["disponibilidad"]}
    r["nivel_ingles"] = {"correcto": pred.get("nivel_ingles") == verdad["nivel_ingles"]}
    return r


def _items(lista):
    return sorted((i["producto"], i["tamano"], i["cantidad"]) for i in lista or [])


def comparar_pedido(pred: dict, verdad: dict, cfg: dict) -> dict:
    promos = cfg["pedido"]["promociones"]
    promo_pred = promos[pred["promocion"]]["descripcion"] if pred.get("promocion") in promos else pred.get("promocion")
    promo_verdad = verdad["promocion"]["descripcion"] if verdad["promocion"] else None
    dir_p, dir_v = pred.get("direccion_entrega") or "", verdad["direccion_entrega"]
    digitos_ok = re.findall(r"\d+", normalizar(dir_p)) == re.findall(r"\d+", normalizar(dir_v))
    tv = _tokens(dir_v)
    cobertura = len(_tokens(dir_p) & tv) / len(tv)
    td = pred.get("total_dicho")
    return {
        "items": {"correcto": _items(pred.get("items")) == _items(verdad["items"])},
        "promocion": {"correcto": promo_pred == promo_verdad},
        "direccion_entrega": {"correcto": digitos_ok and cobertura >= 0.8,
                              "digitos_ok": digitos_ok, "cobertura_tokens": round(cobertura, 2)},
        "metodo_pago": {"correcto": pred.get("metodo_pago") == verdad["metodo_pago"]},
        "total_dicho": {"correcto": td is not None and abs(td - verdad["total_dicho"]) < 0.01,
                        "error_abs": None if td is None else abs(td - verdad["total_dicho"])},
    }
