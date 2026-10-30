"""Extracción con un modelo de lenguaje local (Qwen) que devuelve JSON.

El modelo devuelve, por campo, {"valor", "cita"}. La cita es la evidencia que después exige la
regla de verificación: si el modelo parafrasea o «corrige» la transcripción, el campo queda sin verificar.
"""
import json
import re
from datetime import date
from functools import lru_cache

from .extraccion_reglas import resolver_fecha
from .numeros import normalizar


@lru_cache(maxsize=1)
def _cargar(nombre):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(nombre)
    modelo = AutoModelForCausalLM.from_pretrained(
        nombre, torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None)
    return tok, modelo


def preguntar(transcripcion: str, prompt: str, cfg_llm: dict) -> str:
    tok, modelo = _cargar(cfg_llm["modelo"])
    mensajes = [{"role": "system", "content": prompt},
                {"role": "user", "content": f"Transcripción:\n{transcripcion}"}]
    entrada = tok.apply_chat_template(mensajes, add_generation_prompt=True, return_tensors="pt").to(modelo.device)
    salida = modelo.generate(entrada, max_new_tokens=cfg_llm["max_tokens_nuevos"], do_sample=False)
    return tok.decode(salida[0, entrada.shape[1]:], skip_special_tokens=True)


def leer_json(respuesta: str) -> dict:
    m = re.search(r"\{.*\}", respuesta, re.S)
    return json.loads(m.group(0)) if m else {}


def _par(d, clave):
    v = d.get(clave)
    return (v.get("valor"), v.get("cita")) if isinstance(v, dict) else (v, None)


def a_registro(respuesta: str, esquema: str, cfg: dict):
    """Convierte el JSON del modelo al mismo formato (campos, evidencias) que las reglas."""
    d = leer_json(respuesta)
    campos, evid = {}, {}
    if esquema == "entrevista":
        for c in ("anios_experiencia", "ultimo_puesto", "nivel_ingles"):
            campos[c], evid[c] = _par(d, c)
        if campos["anios_experiencia"] is not None:
            campos["anios_experiencia"] = float(campos["anios_experiencia"])
        if campos["nivel_ingles"]:
            campos["nivel_ingles"] = {"basico": "básico"}.get(normalizar(campos["nivel_ingles"]),
                                                              normalizar(campos["nivel_ingles"]))
        tecnos, cita = _par(d, "tecnologias")
        alias = cfg["entrevista"]["tecnologias"]
        canon = {normalizar(a): k for k, v in alias.items() for a in v + [k]}
        campos["tecnologias"] = [canon.get(normalizar(x), x) for x in tecnos or []]
        evid["tecnologias"] = list(tecnos or [])                 # cada tecnología debe estar en el texto
        sal, evid["pretension_salarial"] = _par(d, "pretension_salarial")
        campos["pretension_salarial"] = ({"monto": float(sal["monto"]), "moneda": sal.get("moneda", "PEN")}
                                         if isinstance(sal, dict) and sal.get("monto") is not None else None)
        disp, evid["disponibilidad"] = _par(d, "disponibilidad")
        campos["disponibilidad"] = (resolver_fecha(normalizar(str(disp)), date.fromisoformat(cfg["fecha_escena"]))
                                    if disp else None)
    else:
        cp = cfg["pedido"]
        items, citas = _par(d, "items")
        campos["items"], evid["items"] = [], []
        citas = citas if isinstance(citas, list) else [citas] * len(items or [])
        for it, cita in zip(items or [], citas):
            prod = normalizar(it.get("producto", ""))
            producto = next((p for p, al in cp["alias_productos"].items()
                             if any(re.fullmatch(a, prod) for a in al) or normalizar(p) == prod), None)
            if not producto:
                continue
            tam = normalizar(str(it.get("tamano") or ""))
            tam = next((t for t, al in cp["alias_tamanos"].items() if any(re.fullmatch(a, tam) for a in al)),
                       cp["tamano_por_defecto"][producto])
            tam = tam if tam in cp["carta"][producto] else cp["tamano_por_defecto"][producto]
            campos["items"].append({"producto": producto, "tamano": tam, "cantidad": int(it.get("cantidad") or 0),
                                    "precio_unitario": cp["carta"][producto][tam]})
            evid["items"].append(cita)
        promo, evid["promocion"] = _par(d, "promocion")
        campos["promocion"] = next((k for k, p in cp["promociones"].items()
                                    if promo and re.search(p["patron"], normalizar(str(promo)))), None)
        campos["direccion_entrega"], evid["direccion_entrega"] = _par(d, "direccion_entrega")
        if campos["direccion_entrega"]:
            campos["direccion_entrega"] = normalizar(campos["direccion_entrega"])
        pago, evid["metodo_pago"] = _par(d, "metodo_pago")
        campos["metodo_pago"] = normalizar(pago) if pago else None
        total, evid["total_dicho"] = _par(d, "total_dicho")
        campos["total_dicho"] = float(total) if total is not None else None
    return campos, evid


def extraer(transcripcion: str, esquema: str, cfg: dict):
    cfg_llm = cfg["extraccion"]["llm"]
    respuesta = preguntar(transcripcion, cfg_llm[f"prompt_{esquema}"], cfg_llm)
    campos, evid = a_registro(respuesta, esquema, cfg)
    return campos, evid, respuesta
