"""Voz a registro · app de Streamlit.

Lee resultados precalculados (resultados/ y cache/); no transcribe el corpus al arrancar.
Solo el probador llama al motor, y únicamente cuando se sube un audio y se pulsa el botón.
"""
import json
import tempfile
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from motor import cargar_config, procesar

RAIZ = Path(__file__).resolve().parent
cfg = cargar_config()
R = cfg["rutas"]
NIVELES = ["L0", "L1", "L2", "L3"]
CORRIDA_BASE = "large-v3-turbo_float16_cuda_glosario-ninguno"

st.set_page_config(page_title="Voz a registro", page_icon=":material/graphic_eq:", layout="wide")


@st.cache_data
def leer_resultados():
    carpeta = RAIZ / R["resultados"]
    leer = lambda n: pd.read_csv(carpeta / n) if (carpeta / n).exists() else pd.DataFrame()
    resumen = json.loads((carpeta / "resumen.json").read_text(encoding="utf-8")) if (carpeta / "resumen.json").exists() else {}
    return (resumen, leer("transcripcion_por_clip.csv"), leer("registro_por_campo.csv"),
            leer("validacion.csv"), leer("wer_vs_registro.csv"))


@st.cache_data
def leer_verdad():
    v = RAIZ / R["verdad"]
    return (json.loads((v / "entrevistas.json").read_text(encoding="utf-8"))["clips"],
            json.loads((v / "llamadas.json").read_text(encoding="utf-8"))["clips"],
            {p.stem: p.read_text(encoding="utf-8") for p in (v / "referencias").glob("*.txt")})


@st.cache_data
def leer_transcripcion(corrida, clip):
    p = RAIZ / R["cache"] / "transcripciones" / corrida / f"{clip}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def corrida_principal(nivel="L0"):
    carpeta = RAIZ / R["cache"] / "transcripciones"
    preferida = f"{nivel}_{CORRIDA_BASE}"
    if (carpeta / preferida).exists():
        return preferida
    otras = sorted(p.name for p in carpeta.glob(f"{nivel}_*")) if carpeta.exists() else []
    return otras[0] if otras else None


resumen, asr_df, reg_df, val_df, wer_vs = leer_resultados()
verdad_e, verdad_l, referencias = leer_verdad()

st.title("Voz a registro")
st.caption("De una entrevista grabada a una ficha de candidato, y de una llamada de venta a un pedido que se revisa solo.")

problema, corpus, resultados, pedidos, probador = st.tabs(
    [":material/lightbulb: Problema y método", ":material/library_music: Corpus",
     ":material/analytics: Resultados", ":material/receipt_long: Pedidos", ":material/upload: Probador"])

with problema:
    st.subheader("El audio que nadie procesa")
    st.markdown(
        "El celular ya transcribe notas de voz, pero lo que una organización necesita no es texto: son **campos "
        "verificados, en una tabla, con una medida de cuánto confiar en ellos**. Este proyecto convierte audio en "
        "registros y dice qué campos se pueden creer.")
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("**Se hace una sola vez**")
            st.markdown("1. Guiones con datos inventados → la verdad de cada clip sale gratis\n"
                        "2. Grabación en parejas (10 clips, ~26 min)\n"
                        "3. Escalera de degradación L1–L3\n"
                        "4. Transcripción en GPU (Colab) y caché en el repositorio\n"
                        "5. Métricas desde la caché")
    with c2:
        with st.container(border=True):
            st.markdown("**Se hace con cada audio nuevo** · `motor.procesar(ruta, esquema)`")
            st.markdown("1. Transcripción (faster-whisper)\n"
                        "2. Números dichos → cifras\n"
                        "3. Extracción de campos (reglas o Qwen)\n"
                        "4. Verificación literal de cada campo\n"
                        "5. Solo en pedidos: validación aritmética y diagnóstico")
    st.markdown("**Regla de verificación:** un valor solo se acepta si su fragmento de origen está literalmente en la "
                "transcripción. Un modelo que «corrige» lo que el ASR oyó mal deja el campo *sin verificar*, aunque acierte.")

with corpus:
    clips = sorted(referencias)
    clip = st.selectbox("Clip", clips, format_func=lambda c: f"{c} · {'entrevista' if c[0] == 'E' else 'llamada'}")
    audio = next((RAIZ / R["audio"]).glob(f"{clip}.*"), None) if (RAIZ / R["audio"]).exists() else None
    if audio:
        st.audio(str(audio))
    else:
        st.info("Los audios no están en el repositorio (ver README, «Audios»). Se muestran las transcripciones.",
                icon=":material/info:")
    izq, der = st.columns(2)
    with izq:
        st.markdown("**Referencia** (escrita y revisada a mano)")
        with st.container(height=420):
            st.text(referencias[clip])
    with der:
        corrida = corrida_principal()
        t = leer_transcripcion(corrida, clip) if corrida else None
        st.markdown(f"**Transcripción** · `{corrida}`" if t else "**Transcripción**")
        with st.container(height=420):
            st.text(t["texto"] if t else "Aún no hay transcripción en la caché.")
    st.markdown("**Registro correcto**")
    st.json(verdad_e.get(clip) or verdad_l.get(clip), expanded=False)

with resultados:
    if not resumen:
        st.warning("Todavía no hay resultados: corre `python scripts/evaluar.py`.", icon=":material/hourglass_empty:")
    else:
        st.subheader("Capa 1 · transcripción")
        tabla = pd.DataFrame(resumen["transcripcion"])
        tabla["wer_ic95"] = tabla["wer_ic95"].map(lambda x: f"[{x[0]:.3f}, {x[1]:.3f}]")
        st.dataframe(tabla, hide_index=True, alt="WER, CER, velocidad y VRAM por corrida",
                     column_config={"wer": st.column_config.NumberColumn("WER", format="%.3f"),
                                    "cer": st.column_config.NumberColumn("CER", format="%.3f"),
                                    "segundos_por_minuto": st.column_config.NumberColumn("s / min de audio", format="%.1f"),
                                    "vram_pico_mb": st.column_config.NumberColumn("VRAM pico (MB)", format="%.0f"),
                                    "vram_total_usada_mb": st.column_config.NumberColumn("VRAM total (MB)", format="%.0f")})
        if resumen.get("comparaciones_texto"):
            st.markdown("**¿Cambió el texto?** (corridas que difieren en una sola cosa)")
            st.dataframe(pd.DataFrame(resumen["comparaciones_texto"]), hide_index=True, alt="Cambios de texto entre corridas")
        if resumen.get("glosario"):
            st.markdown("**Glosario de dominio** · diferencia pareada de WER (negativo = mejora)")
            st.dataframe(pd.DataFrame(resumen["glosario"]), hide_index=True, alt="Efecto del glosario en el WER")

        st.subheader("Capa 2 · registro")
        reg = pd.DataFrame(resumen["registro"])
        nivel0 = reg[reg.corrida.str.startswith("L0") & reg.corrida.str.contains("float16_cuda_glosario-ninguno|int8_cpu")]
        vista = nivel0.pivot_table(index=["tarea", "campo"], columns=["metodo"], values="exactitud").reset_index()
        st.dataframe(vista, hide_index=True, alt="Exactitud por campo, reglas contra modelo de lenguaje",
                     column_config={m: st.column_config.ProgressColumn(m, min_value=0, max_value=1, format="%.2f")
                                    for m in ("reglas", "llm")})
        if resumen.get("macro_f1"):
            st.dataframe(pd.DataFrame(resumen["macro_f1"]), hide_index=True, alt="F1 macro del nivel de inglés")

        st.subheader("¿El WER predice si el registro sirve?")
        if len(wer_vs):
            grafico = alt.Chart(wer_vs).mark_circle(size=90).encode(
                x=alt.X("wer:Q", title="WER del clip"),
                y=alt.Y("exactitud_registro:Q", title="Campos correctos", scale=alt.Scale(domain=[0, 1])),
                color=alt.Color("corrida:N", legend=alt.Legend(orient="bottom", columns=2)),
                tooltip=["clip", "corrida", alt.Tooltip("wer:Q", format=".3f"), alt.Tooltip("exactitud_registro:Q", format=".2f")])
            st.altair_chart(grafico, alt="Dispersión entre el WER de cada clip y la proporción de campos correctos")

with pedidos:
    if len(val_df) == 0:
        st.warning("Todavía no hay validaciones en resultados/.", icon=":material/hourglass_empty:")
    else:
        st.subheader("Escalera de degradación")
        asr_l = asr_df.assign(nivel=asr_df.corrida.str[:2])
        asr_l = asr_l[asr_l.corrida.str.endswith(CORRIDA_BASE)]
        reg_l = reg_df.assign(nivel=reg_df.corrida.str[:2])
        reg_l = reg_l[reg_l.corrida.str.endswith(CORRIDA_BASE)]
        curva = pd.concat([
            asr_l.groupby(["nivel", "tarea"]).wer.mean().rename("valor").reset_index().assign(metrica="WER"),
            reg_l[reg_l.metodo == "reglas"].groupby(["nivel", "tarea"]).correcto.mean().rename("valor").reset_index()
            .assign(metrica="exactitud de campos (reglas)"),
            reg_l[reg_l.metodo == "llm"].groupby(["nivel", "tarea"]).correcto.mean().rename("valor").reset_index()
            .assign(metrica="exactitud de campos (LLM)")])
        if len(curva):
            st.altair_chart(alt.Chart(curva).mark_line(point=True).encode(
                x=alt.X("nivel:N", sort=NIVELES, title="Nivel"), y=alt.Y("valor:Q", title=None),
                color=alt.Color("metrica:N", title=None, legend=alt.Legend(orient="bottom")),
                strokeDash=alt.StrokeDash("tarea:N", title="Tarea")),
                alt="WER y exactitud de campos en cada nivel de la escalera")
        st.caption("L1 WhatsApp (Opus 16 kbps) · L2 teléfono (300–3400 Hz, 8 kHz) · "
                   f"L3 L1 + murmullo a {cfg['escalera']['L3']['snr_db']} dB de SNR")

        st.subheader("Atrapados contra perdidos")
        st.dataframe(pd.DataFrame(resumen.get("validacion", [])), hide_index=True,
                     alt="Errores plantados atrapados y perdidos por nivel")
        st.subheader("Cada llamada en cada nivel")
        metodo = st.segmented_control("Extracción", ["reglas", "llm"], default="reglas")
        st.dataframe(val_df[val_df.metodo == metodo].drop(columns="metodo"), hide_index=True,
                     alt="Resultado de la validación aritmética por llamada")

with probador:
    st.subheader("Prueba el motor con tu propio audio")
    with st.form("probar"):
        subido = st.file_uploader("Audio", type=["mp3", "m4a", "wav", "ogg", "opus"])
        esquema = st.segmented_control("Tipo de registro", ["entrevista", "pedido"], default="entrevista")
        enviar = st.form_submit_button("Procesar", icon=":material/play_arrow:", type="primary")
    if enviar and subido:
        with tempfile.NamedTemporaryFile(suffix=Path(subido.name).suffix, delete=False) as f:
            f.write(subido.getbuffer())
        with st.spinner("Transcribiendo y extrayendo…"):
            r = procesar(f.name, esquema)
        if r["error"]:
            st.error(r["error"], title="El motor devolvió un error")
        else:
            st.caption(f"Dispositivo: {r['dispositivo']} · {r['segundos']} s")
            izq, der = st.columns(2)
            with izq:
                st.markdown("**Transcripción**")
                with st.container(height=400):
                    st.text(r["transcripcion"])
            with der:
                st.markdown("**Registro**")
                filas = [{"campo": k, "valor": json.dumps(v, ensure_ascii=False), "estado": r["verificacion"].get(k)}
                         for k, v in r["campos"].items()]
                st.dataframe(pd.DataFrame(filas), hide_index=True, alt="Campos extraídos y su verificación")
                if r["validacion"]:
                    v = r["validacion"]
                    if v["estado"] == "cuadra":
                        st.success(f"El total cuadra: {v['total_calculado']:.2f}", icon=":material/check_circle:")
                    elif v["estado"] == "no_cuadra":
                        st.error(f"Calculado {v['total_calculado']:.2f}, dicho {v['total_dicho']:.2f}. "
                                 f"Diagnóstico: {v['diagnostico']} — {v.get('motivo', '')}",
                                 title="El total no cuadra")
    elif enviar:
        st.warning("Sube un audio primero.")
