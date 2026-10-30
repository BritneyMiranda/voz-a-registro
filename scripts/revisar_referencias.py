"""Lista, con su minuto, cada lugar donde el guion y la transcripción de Whisper no coinciden.

La referencia no se puede copiar de Whisper (sería evaluar al modelo contra sí mismo), pero al grabar nadie
lee el guion palabra por palabra. Este script señala solo los lugares dudosos; la autora escucha cada uno y
corrige verdad/referencias/<clip>.txt cuando lo dicho fue distinto del guion. Si lo que dijo era el guion y
Whisper oyó mal, la referencia no se toca: eso es justamente un error de ASR.

    python scripts/revisar_referencias.py --corrida L0_large-v3-turbo_int8_cpu_glosario-ninguno
"""
import argparse
import difflib
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from motor import cargar_config  # noqa: E402
from motor.numeros import normalizar  # noqa: E402

cfg = cargar_config()
ap = argparse.ArgumentParser()
ap.add_argument("--corrida", required=True)
args = ap.parse_args()

carpeta = RAIZ / cfg["rutas"]["cache"] / "transcripciones" / args.corrida
salida = [f"# Revisión de referencias\n\nCorrida: `{args.corrida}`. Escucha cada minuto marcado y decide:\n\n"
          "- **Se dijo lo que oyó Whisper** → cambia `verdad/referencias/<clip>.txt` para que diga eso.\n"
          "- **Se dijo el guion** → no cambies nada (es un error de Whisper, y eso es lo que medimos).\n"
          "- Las muletillas («eh», «ya», «este») también van en la referencia si se dijeron.\n"]
total = 0
for p in sorted(carpeta.glob("*.json")):
    r = json.loads(p.read_text(encoding="utf-8"))
    ref = normalizar((RAIZ / cfg["rutas"]["verdad"] / "referencias" / f"{p.stem}.txt").read_text(encoding="utf-8")).split()
    # se normaliza segmento por segmento (no palabra por palabra) para que «seis mil quinientos» siga
    # siendo un solo número; cada palabra hereda el minuto de inicio de su segmento
    hip, tiempos = [], []
    for s in r["segmentos"]:
        for token in normalizar(s["texto"]).split():
            hip.append(token)
            tiempos.append(s["inicio"])
    salida.append(f"\n## {p.stem}\n\n| Minuto | El guion dice | Whisper oyó |\n|---|---|---|")
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=ref, b=hip, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        t = tiempos[min(j1, len(tiempos) - 1)] if tiempos else 0
        contexto = " ".join(ref[max(0, i1 - 3):i1])
        salida.append(f"| {int(t // 60)}:{int(t % 60):02d} | …{contexto} **{' '.join(ref[i1:i2]) or '—'}** "
                      f"| **{' '.join(hip[j1:j2]) or '—'}** |")
        total += 1
destino = RAIZ / "verdad" / "REVISAR.md"
destino.write_text("\n".join(salida) + "\n", encoding="utf-8")
print(f"{total} diferencias → {destino}")

# misma lista como página local con un botón que reproduce cada lugar (no se versiona: usa los audios)
import html  # noqa: E402
import re  # noqa: E402

PALABRAS_CAMPO = [normalizar(p) for p in list(cfg["pedido"]["carta"]) + list(cfg["entrevista"]["tecnologias"])] + [
    "ceviche", "lomo", "chicha", "kola", "cola", "suspiro", "aji", "chicharron", "arroz", "jarra", "vaso", "fuente",
    "personal", "jiron", "avenida", "calle", "manzana", "lote", "yape", "plin", "tarjeta", "efectivo", "total",
    "descuento", "promocion", "gratis", "soles", "dolares", "anos", "semanas", "mes", "inmediata", "ingles",
    "basico", "intermedio", "avanzado", "analista", "desarrollador", "lider", "jefe", "asistente", "disenadora", "cargo",
    "puesto", "quit", "cambia", "corrijo", "no tres", "mejor"]
filas, clip = [], None
for linea in salida:
    if linea.startswith("\n## "):
        clip = linea.strip("\n# ").strip()
        filas.append(f"<h2>{clip}</h2><audio id='{clip}' src='../audio/{clip}.mp3' preload='none'></audio>"
                     "<table><tr><th></th><th>Minuto</th><th>El guion dice</th><th>Whisper oyó</th><th>Se dijo…</th></tr>")
    elif linea.startswith("| ") and clip and not linea.startswith("| Minuto"):
        minuto, guion, oido = [c.strip() for c in linea.strip("|").split("|")]
        m, s = map(int, minuto.split(":"))
        seg = max(0, m * 60 + s - 2)
        b = lambda x: re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", html.escape(x))
        # prioritaria: lo que difiere toca un número o una palabra de los campos del registro
        dif = " ".join(re.findall(r"\*\*(.*?)\*\*", guion + " " + oido))
        prioritaria = bool(re.search(r"\d|" + "|".join(PALABRAS_CAMPO), dif))
        filas.append(f"<tr class='{'prio' if prioritaria else 'resto'}'><td><button onclick=\"oir('{clip}',{seg})\">▶</button></td><td>{minuto}</td>"
                     f"<td>{b(guion)}</td><td>{b(oido)}</td><td><select><option></option><option>el guion</option>"
                     "<option>lo de Whisper</option><option>otra cosa</option></select></td></tr>")
pagina = ("<!doctype html><meta charset='utf-8'><title>Revisar referencias</title><style>"
          "body{font:15px system-ui;max-width:1000px;margin:24px auto;padding:0 16px}"
          "table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;padding:6px;text-align:left}"
          "button{font-size:16px;cursor:pointer}tr.prio{background:#fff4c2}"
          "body.solo tr.resto{display:none}</style><h1>Revisar referencias</h1>"
          "<p><label><input type='checkbox' checked onchange=\"document.body.classList.toggle('solo',this.checked)\"> "
          "Mostrar solo las prioritarias (en amarillo: tocan números o datos del registro)</label></p>"
          "<p>▶ reproduce 8 segundos desde un poco antes de la diferencia. Si se dijo lo que oyó Whisper (u otra cosa), "
          "corrige <code>verdad/referencias/&lt;clip&gt;.txt</code>. Si se dijo el guion, no cambies nada.</p>"
          + "".join(f + ("</table>" if f.startswith("<tr>") and (i + 1 == len(filas) or filas[i + 1].startswith("<h2>")) else "")
                    for i, f in enumerate(filas))
          + "<script>document.body.classList.add('solo');let t;function oir(c,s){document.querySelectorAll('audio').forEach(a=>a.pause());"
            "const a=document.getElementById(c);a.currentTime=s;a.play();clearTimeout(t);t=setTimeout(()=>a.pause(),8000)}"
            "</script>")
(RAIZ / "verdad" / "revisar.html").write_text(pagina, encoding="utf-8")
