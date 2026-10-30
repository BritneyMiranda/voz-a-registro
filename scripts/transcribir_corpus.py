"""Transcribe el corpus una vez y guarda cada resultado en la caché (cache/transcripciones/<corrida>/<clip>.json).

La app, la evaluación y GitHub Actions leen solo esta caché: nunca vuelven a transcribir.

Ejemplos:
    python scripts/transcribir_corpus.py                                   # config.yaml tal cual, nivel L0
    python scripts/transcribir_corpus.py --nivel L3
    python scripts/transcribir_corpus.py --modelo small --precision float16 --dispositivo cuda
    python scripts/transcribir_corpus.py --glosario hotwords
"""
import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from motor import asr, cargar_config  # noqa: E402

cfg = cargar_config()
ap = argparse.ArgumentParser()
ap.add_argument("--nivel", default="L0", help="L0 = audio original; L1-L3 = escalera de degradación")
ap.add_argument("--modelo", help="clave de asr.modelos_comparacion o nombre completo del modelo")
ap.add_argument("--precision")
ap.add_argument("--dispositivo")
ap.add_argument("--glosario", choices=["ninguno", "hotwords", "initial_prompt"])
ap.add_argument("--clips", nargs="*", help="por defecto, todos los audios de la carpeta")
ap.add_argument("--forzar", action="store_true", help="rehacer aunque ya esté en la caché")
args = ap.parse_args()

conf = dict(cfg["asr"])
alias = None
if args.modelo:
    alias = args.modelo if args.modelo in conf["modelos_comparacion"] else None
    conf["modelo"] = conf["modelos_comparacion"].get(args.modelo, args.modelo)
for clave in ("precision", "dispositivo"):
    if getattr(args, clave):
        conf[clave] = getattr(args, clave)
if args.glosario:
    conf["glosario_modo"] = args.glosario
if conf["dispositivo"] == "auto":
    import ctranslate2
    conf["dispositivo"] = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"

carpeta_audio = RAIZ / (cfg["rutas"]["audio"] if args.nivel == "L0" else Path(cfg["rutas"]["audio_degradado"]) / args.nivel)
nombre_modelo = alias or conf["modelo"].split("/")[-1].replace("faster-whisper-", "")
corrida = f"{args.nivel}_{nombre_modelo}_{conf['precision']}_{conf['dispositivo']}_glosario-{conf['glosario_modo']}"
destino = RAIZ / cfg["rutas"]["cache"] / "transcripciones" / corrida
destino.mkdir(parents=True, exist_ok=True)

audios = sorted(p for p in carpeta_audio.iterdir() if p.suffix.lower() in (".mp3", ".m4a", ".wav", ".ogg", ".opus"))
if args.clips:
    audios = [a for a in audios if a.stem in args.clips]
print(f"{corrida}: {len(audios)} clips", flush=True)
for audio in audios:
    salida = destino / f"{audio.stem}.json"
    if salida.exists() and not args.forzar:
        continue
    esquema = "entrevista" if audio.stem.startswith("E") else "pedido"
    glosario = cfg["glosario"][esquema] if conf["glosario_modo"] != "ninguno" else ""
    r = asr.transcribir(str(audio), conf, glosario)
    r["clip"], r["nivel"] = audio.stem, args.nivel
    salida.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {audio.stem}: {r['duracion_audio_s']:.0f} s de audio, {r['segundos_transcripcion']:.0f} s, "
          f"dispositivo={r['dispositivo']}, vram_pico={r['vram_pico_mb']} MB", flush=True)
