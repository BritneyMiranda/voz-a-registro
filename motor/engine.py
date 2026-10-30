"""El motor: una sola función para las dos tareas.

    procesar(ruta_audio, esquema) -> dict

`esquema` elige el registro ("entrevista" para la Tarea 1, "pedido" para la Tarea 2). Lo único que
cambia entre tareas es qué extractor de campos se llama y si se valida la aritmética; la
transcripción, la verificación y el formato de salida son los mismos.

Este módulo no importa ninguna librería de interfaz (ver README: «Comprobar que el motor no importa UI»).
"""
import json
import os
import time
from pathlib import Path

import yaml

from . import asr, extraccion_reglas, validacion, verificacion

RAIZ = Path(__file__).resolve().parent.parent
EXTRACTORES = {"entrevista": extraccion_reglas.extraer_entrevista,
               "pedido": extraccion_reglas.extraer_pedido}


def cargar_config(ruta=None) -> dict:
    with open(ruta or RAIZ / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cache_modelos = Path(cfg["rutas"]["cache_modelos"])
    if "HF_HOME" not in os.environ and cache_modelos.anchor and Path(cache_modelos.anchor).exists():
        os.environ["HF_HOME"] = str(cache_modelos)            # en Colab esa unidad no existe y se usa la de siempre
    return cfg


def procesar(ruta_audio, esquema: str, metodo: str | None = None, cfg: dict | None = None,
             transcripcion: dict | None = None) -> dict:
    """Audio → transcripción → campos → verificación → (validación aritmética si es un pedido).

    `transcripcion` permite pasar una transcripción ya calculada (la caché) para no volver a usar el ASR.
    Nunca lanza excepciones: si algo falla, lo devuelve en `error`.
    """
    cfg = cfg or cargar_config()
    metodo = metodo or cfg["extraccion"]["metodo"]
    t0 = time.perf_counter()
    resultado = {"audio": str(ruta_audio), "esquema": esquema, "metodo": metodo, "transcripcion": None,
                 "campos": {}, "verificacion": {}, "validacion": None, "dispositivo": None,
                 "segundos": None, "error": None}
    try:
        if esquema not in EXTRACTORES:
            raise ValueError(f"esquema desconocido: {esquema}")
        if transcripcion is None:
            glosario = cfg["glosario"][esquema] if cfg["asr"]["glosario_modo"] != "ninguno" else ""
            transcripcion = asr.transcribir(ruta_audio, cfg["asr"], glosario)
        texto = transcripcion["texto"]
        resultado.update(transcripcion=texto, dispositivo=transcripcion.get("dispositivo"),
                         asr={k: v for k, v in transcripcion.items()
                              if k not in ("texto", "segmentos", "palabras")})
        if metodo == "llm":
            from . import extraccion_llm                        # import diferido: torch solo si se usa
            campos, evid, crudo = extraccion_llm.extraer(texto, esquema, cfg)
            resultado["respuesta_llm"] = crudo
        else:
            campos, evid = EXTRACTORES[esquema](texto, cfg)
        resultado["campos"], resultado["evidencias"] = campos, evid
        resultado["verificacion"] = verificacion.verificar(campos, evid, texto, esquema, cfg)
        if esquema == "pedido":
            resultado["validacion"] = validacion.validar(campos, cfg, transcripcion.get("palabras"))
    except Exception as e:                                     # el error viaja en el resultado
        resultado["error"] = f"{type(e).__name__}: {e}"
    resultado["segundos"] = round(time.perf_counter() - t0, 2)
    return resultado


if __name__ == "__main__":
    import sys
    print(json.dumps(procesar(sys.argv[1], sys.argv[2]), ensure_ascii=False, indent=2))
