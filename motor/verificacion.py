"""Regla de verificación: todo valor extraído tiene que existir literalmente en la transcripción.

Un campo queda «verificado» solo si (1) su evidencia aparece tal cual en la transcripción normalizada y
(2) el valor se deduce de esa evidencia con las mismas reglas deterministas del extractor de reglas.
Si un modelo «corrige» lo que el ASR oyó mal, aunque acierte, el campo queda «sin_verificar».
"""
import re
from datetime import date

from .extraccion_reglas import resolver_fecha
from .numeros import normalizar

VERIFICADO, SIN_VERIFICAR, VACIO = "verificado", "sin_verificar", "vacio"


def _esta(fragmento, texto_norm):
    f = normalizar(str(fragmento))
    return bool(f) and re.search(rf"(?<!\w){re.escape(f)}(?!\w)", texto_norm) is not None


def _numeros(fragmento):
    return {float(x) for x in re.findall(r"\d+(?:\.\d+)?", normalizar(str(fragmento)))}


def verificar(campos: dict, evid: dict, transcripcion: str, esquema: str, cfg: dict) -> dict:
    t = normalizar(transcripcion)
    estado = {}
    for campo, valor in campos.items():
        cita = evid.get(campo)
        if valor in (None, [], ""):
            estado[campo] = VACIO
            continue
        if campo in ("tecnologias", "items"):
            citas = cita if isinstance(cita, list) else []
            ok = len(citas) == len(valor) and all(_esta(c, t) for c in citas)
            if campo == "items" and ok:
                ok = all(it["cantidad"] in _numeros(c) for it, c in zip(valor, citas))
            estado[campo] = VERIFICADO if ok else SIN_VERIFICAR
            continue
        if not cita or not _esta(cita, t):
            estado[campo] = SIN_VERIFICAR
            continue
        if campo in ("anios_experiencia", "total_dicho"):
            ok = float(valor) in _numeros(cita)
        elif campo == "pretension_salarial":
            ok = float(valor["monto"]) in _numeros(cita)
        elif campo == "disponibilidad":
            ok = resolver_fecha(normalizar(cita), date.fromisoformat(cfg["fecha_escena"])) == valor
        elif campo == "nivel_ingles":
            alias = cfg["entrevista"]["niveles_ingles"].get(valor, [])
            ok = any(re.search(rf"\b{a}\b", normalizar(cita)) for a in alias)
        elif campo == "metodo_pago":
            ok = any(re.search(rf"\b{a}\b", normalizar(cita)) for a in cfg["pedido"]["pagos"].get(valor, []))
        elif campo == "promocion":
            promo = cfg["pedido"]["promociones"].get(valor)
            ok = promo is not None and re.search(promo["patron"], normalizar(cita)) is not None
        else:                                                    # textos: el valor debe estar en la cita
            ok = normalizar(valor) in normalizar(cita)
        estado[campo] = VERIFICADO if ok else SIN_VERIFICAR
    return estado
