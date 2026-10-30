"""Escalera de degradación reproducible: audio/ → audio_degradado/L1, L2, L3.

L1  nota de voz de WhatsApp: Opus a 16 kbps, mono.
L2  llamada telefónica: paso banda 300–3400 Hz y remuestreo a 8 kHz.
L3  ambiente ruidoso: L1 + murmullo de conversaciones a una SNR medida.

Cómo se mide la SNR de L3: la potencia de la señal es la media de x² sobre los tramos con voz
(ventanas de 30 ms cuya energía supera −40 dB del máximo), no sobre todo el archivo, para que los
silencios no la bajen. El ruido se escala para que 10·log10(P_voz / P_ruido) sea exactamente snr_db,
y el script vuelve a medirla después de mezclar y la guarda en audio_degradado/L3/snr_medida.json.

El murmullo se arma con `voces_murmullo` clips del propio corpus, invertidos en el tiempo (así suena a
gente hablando pero no se entienden palabras que el ASR pueda copiar) y superpuestos. Semilla fija.
"""
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import soundfile as sf

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from motor import cargar_config  # noqa: E402
from motor.asr import FRECUENCIA, leer_audio  # noqa: E402

cfg = cargar_config()
esc = cfg["escalera"]
FF = imageio_ffmpeg.get_ffmpeg_exe()
origen = RAIZ / cfg["rutas"]["audio"]
base = RAIZ / cfg["rutas"]["audio_degradado"]
audios = sorted(p for p in origen.iterdir() if p.suffix.lower() in (".mp3", ".m4a", ".wav"))


def ffmpeg(*args):
    subprocess.run([FF, "-v", "error", "-y", *map(str, args)], check=True)


def potencia_voz(x, ventana=480):
    n = len(x) // ventana
    energias = (x[: n * ventana].reshape(n, ventana) ** 2).mean(axis=1)
    umbral = energias.max() * 10 ** (-40 / 10)
    return energias[energias > umbral].mean()


# L1: WhatsApp
(base / "L1").mkdir(parents=True, exist_ok=True)
for a in audios:
    ffmpeg("-i", a, "-ac", esc["L1"]["canales"], "-c:a", esc["L1"]["codec"], "-b:a", esc["L1"]["bitrate"],
           "-application", "voip", base / "L1" / f"{a.stem}.ogg")

# L2: teléfono
(base / "L2").mkdir(parents=True, exist_ok=True)
bajo, alto = esc["L2"]["paso_banda_hz"]
for a in audios:
    ffmpeg("-i", a, "-ac", 1, "-af", f"highpass=f={bajo}:poles=2,lowpass=f={alto}:poles=2",
           "-ar", esc["L2"]["frecuencia_muestreo"], base / "L2" / f"{a.stem}.wav")

# L3: L1 + murmullo a SNR fija
(base / "L3").mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(esc["semilla"])
snr = esc["L3"]["snr_db"]
medidas = {}
for a in audios:
    voz = leer_audio(base / esc["L3"]["base"] / f"{a.stem}.ogg")
    otros = [p for p in audios if p.stem != a.stem]
    elegidos = rng.choice(len(otros), size=min(esc["L3"]["voces_murmullo"], len(otros)), replace=False)
    murmullo = np.zeros_like(voz)
    for i in elegidos:
        o = leer_audio(otros[i])[::-1]
        o = np.resize(o, len(voz))                           # repite si el otro clip es más corto
        murmullo += o / (np.sqrt(potencia_voz(o)) + 1e-9)
    escala = np.sqrt(potencia_voz(voz) / (murmullo ** 2).mean() / 10 ** (snr / 10))
    ruido = murmullo * escala
    mezcla = voz + ruido
    mezcla /= max(1.0, np.abs(mezcla).max() / 0.99)          # evita saturar sin cambiar la SNR
    medida = 10 * np.log10(potencia_voz(voz) / (ruido ** 2).mean())
    medidas[a.stem] = round(float(medida), 2)
    sf.write(base / "L3" / f"{a.stem}.wav", mezcla, FRECUENCIA)
(base / "L3" / "snr_medida.json").write_text(json.dumps({"snr_objetivo_db": snr, "snr_medida_db": medidas},
                                                        indent=1), encoding="utf-8")
print("L1, L2 y L3 listos;", "SNR medida:", medidas)
