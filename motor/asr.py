"""Transcripción con faster-whisper, con medición del dispositivo real y de la VRAM.

El dispositivo NO se toma de config.yaml: se lee del modelo ya cargado (ctranslate2 expone `device`
y `compute_type`). Una configuración que pide "cuda" y una librería que cae a CPU en silencio se
distinguen solo así, junto con la VRAM medida por NVML mientras transcribe.
"""
import subprocess
import threading
import time
from functools import lru_cache

import imageio_ffmpeg
import numpy as np

FRECUENCIA = 16000


def leer_audio(ruta: str) -> np.ndarray:
    """Decodifica cualquier formato con ffmpeg a mono 16 kHz float32."""
    salida = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(ruta),
         "-ac", "1", "-ar", str(FRECUENCIA), "-f", "f32le", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(salida, np.float32)


class MedidorVRAM:
    """Muestrea la memoria de la GPU cada 50 ms en un hilo y guarda el pico."""

    def __init__(self, intervalo=0.05):
        self.intervalo, self.pico, self.base, self._activo = intervalo, None, None, False
        try:
            import pynvml
            pynvml.nvmlInit()
            self._nvml = pynvml
            self._gpu = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception:
            self._nvml = None                                   # sin GPU NVIDIA: no hay nada que medir

    def _usada_mb(self):
        return self._nvml.nvmlDeviceGetMemoryInfo(self._gpu).used / 2**20

    def __enter__(self):
        if self._nvml:
            self.base = self.pico = self._usada_mb()
            self._activo = True
            self._hilo = threading.Thread(target=self._muestrear, daemon=True)
            self._hilo.start()
        return self

    def _muestrear(self):
        while self._activo:
            self.pico = max(self.pico, self._usada_mb())
            time.sleep(self.intervalo)

    def __exit__(self, *_):
        self._activo = False
        if self._nvml:
            self._hilo.join()

    @property
    def gpu(self):
        return self._nvml.nvmlDeviceGetName(self._gpu) if self._nvml else None


@lru_cache(maxsize=4)
def cargar_modelo(nombre: str, dispositivo: str, precision: str):
    from faster_whisper import WhisperModel
    return WhisperModel(nombre, device=dispositivo, compute_type=precision)


def transcribir(ruta_audio: str, asr: dict, glosario: str = "") -> dict:
    """Transcribe un audio. `asr` es la sección `asr` de config.yaml."""
    audio = leer_audio(ruta_audio)
    with MedidorVRAM() as vram:
        t0 = time.perf_counter()
        modelo = cargar_modelo(asr["modelo"], asr["dispositivo"], asr["precision"])
        t_carga = time.perf_counter() - t0
        opciones = dict(language=asr["idioma"], beam_size=asr["beam_size"],
                        vad_filter=asr["vad"], word_timestamps=True)
        if glosario and asr.get("glosario_modo") == "hotwords":
            opciones["hotwords"] = glosario
        elif glosario and asr.get("glosario_modo") == "initial_prompt":
            opciones["initial_prompt"] = glosario
        t1 = time.perf_counter()
        segmentos, info = modelo.transcribe(audio, **opciones)
        segmentos = list(segmentos)                             # el generador transcribe al recorrerlo
        t_trans = time.perf_counter() - t1
    palabras = [{"palabra": p.word.strip(), "inicio": round(p.start, 2), "fin": round(p.end, 2),
                 "prob": round(p.probability, 3)} for s in segmentos for p in (s.words or [])]
    duracion = len(audio) / FRECUENCIA
    return {
        "texto": " ".join(s.text.strip() for s in segmentos),
        "segmentos": [{"inicio": round(s.start, 2), "fin": round(s.end, 2), "texto": s.text.strip()}
                      for s in segmentos],
        "palabras": palabras,
        "modelo": asr["modelo"],
        "dispositivo": modelo.model.device,                     # leído de ctranslate2, no de la config
        "precision": modelo.model.compute_type,
        "gpu": vram.gpu if modelo.model.device == "cuda" else None,
        "vram_pico_mb": round(vram.pico - vram.base, 1) if vram.pico is not None else None,
        "vram_total_usada_mb": round(vram.pico, 1) if vram.pico is not None else None,
        "duracion_audio_s": round(duracion, 2),
        "segundos_carga": round(t_carga, 2),
        "segundos_transcripcion": round(t_trans, 2),
        "segundos_por_minuto": round(t_trans / (duracion / 60), 2),
        "glosario_modo": asr.get("glosario_modo", "ninguno") if glosario else "ninguno",
    }
