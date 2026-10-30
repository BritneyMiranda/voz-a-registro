"""Genera notebooks/colab_gpu.ipynb (más fácil de mantener como código que como JSON)."""
import json
from pathlib import Path

REPO = "https://github.com/BritneyMiranda/voz-a-registro.git"
celdas = [
    ("md", "# Mediciones en GPU · Voz a registro\n\nEntorno de ejecución → Cambiar tipo → **GPU T4**. "
           "Luego Entorno de ejecución → **Ejecutar todas**. Tarda unos 40 minutos.\n\n"
           "Antes: sube los 10 audios (`E01.mp3` … `L05.mp3`) a la carpeta `voz_a_registro_audio` de tu Google Drive."),
    ("md", "## 1. ¿Hay GPU? (lo que dice el hardware, no la configuración)"),
    ("code", "!nvidia-smi"),
    ("md", "## 2. Código, dependencias y audios"),
    ("code", f"!git clone -q {REPO} 2>/dev/null || (cd voz-a-registro && git pull -q)\n"
             "%cd /content/voz-a-registro\n!pip install -q -r requirements-colab.txt"),
    ("code", "from google.colab import drive\ndrive.mount('/content/drive')\n"
             "!mkdir -p audio && cp /content/drive/MyDrive/voz_a_registro_audio/*.mp3 audio/ && ls audio"),
    ("code", "import ctranslate2, torch\nprint('GPUs que ve ctranslate2:', ctranslate2.get_cuda_device_count())\n"
             "print('torch.cuda:', torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"),
    ("md", "## 3. Escalera de degradación (L1 WhatsApp, L2 teléfono, L3 ruido)"),
    ("code", "!python scripts/degradar.py"),
    ("md", "## 4. Transcripciones\nCada corrida es un proceso nuevo, así la VRAM medida incluye cargar el modelo."),
    ("code", "corridas = [\n"
             "    '--modelo large-v3-turbo --precision float16 --dispositivo cuda',\n"
             "    '--modelo large-v3-turbo --precision int8 --dispositivo cuda',\n"
             "    '--modelo small --precision float16 --dispositivo cuda',\n"
             "    '--modelo small --precision int8 --dispositivo cuda',\n"
             "    '--modelo large-v3-turbo --precision float16 --dispositivo cuda --glosario hotwords',\n"
             "    '--modelo large-v3-turbo --precision float16 --dispositivo cuda --glosario initial_prompt',\n"
             "    '--modelo large-v3-turbo --precision float16 --dispositivo cuda --nivel L1',\n"
             "    '--modelo large-v3-turbo --precision float16 --dispositivo cuda --nivel L2',\n"
             "    '--modelo large-v3-turbo --precision float16 --dispositivo cuda --nivel L3',\n"
             "    # CPU contra GPU en la MISMA máquina, sobre dos clips (en CPU es ~40 veces más lento)\n"
             "    '--modelo large-v3-turbo --precision int8 --dispositivo cpu --clips E01 L01',\n"
             "]\n"
             "for c in corridas:\n    print('>>>', c)\n    !python scripts/transcribir_corpus.py {c}"),
    ("md", "## 5. Extracción con Qwen (modelo de lenguaje local, en la GPU)"),
    ("code", "!python scripts/extraer_llm.py --corridas "
             "L0_large-v3-turbo_float16_cuda_glosario-ninguno L1_large-v3-turbo_float16_cuda_glosario-ninguno "
             "L2_large-v3-turbo_float16_cuda_glosario-ninguno L3_large-v3-turbo_float16_cuda_glosario-ninguno"),
    ("md", "## 6. Métricas y descarga\nDescarga `cache_colab.zip` y pásalo a la carpeta del proyecto."),
    ("code", "!nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv > cache/gpu_colab.csv\n"
             "!python scripts/evaluar.py\n!zip -qr cache_colab.zip cache resultados\n"
             "!cp cache_colab.zip /content/drive/MyDrive/voz_a_registro_audio/\n"
             "from google.colab import files\nfiles.download('cache_colab.zip')"),
]
nb = {"nbformat": 4, "nbformat_minor": 5,
      "metadata": {"accelerator": "GPU", "colab": {"gpuType": "T4"},
                   "kernelspec": {"name": "python3", "display_name": "Python 3"}},
      "cells": [{"cell_type": "markdown" if t == "md" else "code", "metadata": {}, "source": s,
                 **({"outputs": [], "execution_count": None} if t == "code" else {})} for t, s in celdas]}
destino = Path(__file__).resolve().parent.parent / "notebooks" / "colab_gpu.ipynb"
destino.parent.mkdir(exist_ok=True)
destino.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print(destino)
