"""Validación aritmética del pedido y diagnóstico del descuadre.

Σ cantidad × precio − descuento de la promoción debe ser igual a `total_dicho`. Si no cuadra, hay dos
causas posibles y la regla las separa así:

1. Error del hablante: el total dicho coincide exactamente con un error de cuenta típico
   (olvidar la promoción, aplicar dos promociones no acumulables, descontar dos veces).
   Esa coincidencia exacta es muy improbable por azar, así que se toma como evidencia.
2. Posible error de ASR: si no coincide con ninguno, y alguna cifra del pedido o del total tiene
   probabilidad de palabra baja en Whisper (< confianza_minima_numero), se culpa al ASR.
3. Si no hay ninguna de las dos señales: indeterminado. Se reporta, no se adivina.
"""
import re

from .numeros import normalizar

CUADRA, NO_CUADRA, SIN_DATOS = "cuadra", "no_cuadra", "sin_datos"


def descuento(items, clave_promo, cfg):
    if not clave_promo:
        return 0.0
    promo = cfg["pedido"]["promociones"][clave_promo]
    subtotal = sum(i["cantidad"] * i["precio_unitario"] for i in items)
    if promo["tipo"] == "fijo":
        return float(promo["monto"]) if subtotal >= promo["minimo"] else 0.0
    if promo["tipo"] == "dos_por_uno":
        return float(sum((i["cantidad"] // 2) * i["precio_unitario"]
                         for i in items if i["producto"] == promo["producto"]))
    if promo["tipo"] == "gratis":
        return float(sum(i["precio_unitario"] for i in items
                         if i["producto"] == promo["producto"] and i["tamano"] == promo["tamano"]))
    return 0.0


def _confianza_numeros(palabras):
    """Probabilidad mínima de Whisper entre las palabras que son cifras o números dichos."""
    probs = [p["prob"] for p in palabras or [] if re.search(r"\d", normalizar(p["palabra"]))]
    return min(probs) if probs else None


def validar(campos: dict, cfg: dict, palabras=None) -> dict:
    items, dicho = campos.get("items") or [], campos.get("total_dicho")
    if not items or dicho is None:
        return {"estado": SIN_DATOS, "diagnostico": None}
    tol = cfg["validacion"]["tolerancia_soles"]
    subtotal = sum(i["cantidad"] * i["precio_unitario"] for i in items)
    desc = descuento(items, campos.get("promocion"), cfg)
    calculado = subtotal - desc
    resultado = {"subtotal": subtotal, "descuento": desc, "total_calculado": calculado,
                 "total_dicho": dicho, "diferencia": round(dicho - calculado, 2)}
    if abs(dicho - calculado) <= tol:
        return {**resultado, "estado": CUADRA, "diagnostico": None}

    todas = sum(descuento(items, k, cfg) for k in cfg["pedido"]["promociones"])
    hipotesis = {
        "olvidó aplicar la promoción": subtotal,
        "aplicó dos promociones no acumulables": subtotal - todas,
        "descontó la promoción dos veces": subtotal - 2 * desc,
    }
    for motivo, valor in hipotesis.items():
        if desc != 0 or motivo != "descontó la promoción dos veces":
            if abs(dicho - valor) <= tol and abs(valor - calculado) > tol:
                return {**resultado, "estado": NO_CUADRA,
                        "diagnostico": "error_hablante", "motivo": motivo}
    confianza = _confianza_numeros(palabras)
    if confianza is not None and confianza < cfg["validacion"]["confianza_minima_numero"]:
        return {**resultado, "estado": NO_CUADRA, "diagnostico": "posible_error_asr",
                "motivo": f"una cifra tiene probabilidad {confianza:.2f} en Whisper"}
    return {**resultado, "estado": NO_CUADRA, "diagnostico": "indeterminado",
            "motivo": "no coincide con un error de cuenta conocido ni hay cifras dudosas"}
