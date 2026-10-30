# Voz a registro

De una entrevista de trabajo grabada a una ficha de candidato, y de una llamada de venta a un pedido que se revisa
solo. Proyecto integrador de reconocimiento de voz (ASR): las dos tareas usan **el mismo motor**.

- **Documento del pipeline (Notion):** https://classy-channel-7f6.notion.site/pipeline_notion-6df6a9ca170d825e928701b2ca46dc62
- **Video (≤ 8 min):** _enlace pendiente_
- **App:** `streamlit run app.py`

## Por qué no basta con el celular

El teléfono ya transcribe notas de voz, pero la transcripción es el principio del trabajo, no el final. Lo que
necesita una organización son **campos verificados, en una tabla, con una medida de cuánto confiar en ellos**.
Este proyecto entrega eso y además dice qué campos no se pueden creer.

## Datos inventados y consentimiento

- **Todo lo que se dice en las grabaciones es inventado**: personas, empresas, sueldos, direcciones, teléfonos y
  pedidos. No hay datos personales reales de nadie.
- **Todas las personas que aparecen en las grabaciones aceptaron participar y que su voz se use en este proyecto.**
  La autora aparece en los 10 clips; la otra voz es de una compañera del curso, que pidió no ser nombrada. _(confirmar)_

## El corpus

| | Tarea 1 · Entrevistas | Tarea 2 · Llamadas |
|---|---|---|
| Clips | 5 (E01–E05) | 5 (L01–L05) |
| Duración | 2:21 a 3:24 (14,5 min) | 1:52 a 2:23 (10,6 min) |
| Roles | A entrevista, B es candidata/o | A vende, B es cliente |
| Guiones | [guiones/entrevistas.md](guiones/entrevistas.md) | [guiones/llamadas.md](guiones/llamadas.md) |
| Verdad de campo | [verdad/entrevistas.json](verdad/entrevistas.json) | [verdad/llamadas.json](verdad/llamadas.json) |

Grabado en parejas por llamada de Discord y exportado a MP3. L05 dura 1:52, un poco menos que el mínimo de
2 minutos; se dejó así y se reporta como limitación.

**De dónde sale la verdad de campo y por qué no costó nada:** los guiones se escribieron antes de grabar, así que los
valores correctos de cada campo se conocían de antemano. La transcripción de referencia empezó siendo el guion
([scripts/referencias_desde_guiones.py](scripts/referencias_desde_guiones.py)) y luego la autora la corrigió escuchando
cada lugar donde lo grabado se apartó del guion ([scripts/revisar_referencias.py](scripts/revisar_referencias.py),
lista en [verdad/REVISAR.md](verdad/REVISAR.md)). Nunca se copió la salida de Whisper como referencia: eso sería medir
al modelo contra sí mismo.

**Cómo varían los campos (Tarea 1):** en cada entrevista los seis campos aparecen en un orden distinto y con trampas
distintas: correcciones («siete años… bueno, seis y medio»), distractores (sueldo actual antes de la pretensión,
«Excel avanzado» cuando el inglés es básico, el entrevistador diciendo «inglés avanzado» como requisito), moneda en
dólares y fechas relativas. La tabla completa está al inicio de [guiones/entrevistas.md](guiones/entrevistas.md).

**Distribución de los campos (Tarea 1):** años de experiencia 1.5 / 3 / 4 / 6.5 / 8; pretensión en soles en 4 clips y
en dólares en 1; disponibilidad: 1 inmediata, 2 en noviembre por fecha relativa, 1 por fecha exacta, 1 en diciembre;
inglés: básico 2, intermedio 1, avanzado 2; entre 5 y 7 tecnologías por clip.

**Trampas plantadas (Tarea 2, dominio restaurante):**

| Llamada | El cliente se corrige | Total dicho erróneo a propósito | Dirección con números |
|---|---|---|---|
| L01 | sí | sí (resta mal el descuento) | sí |
| L02 | sí | no | sí |
| L03 | no | sí (aplica dos promociones no acumulables) | sí |
| L04 | sí | sí (olvida la jarra gratis) | sí (manzana y lote) |
| L05 | no | no (llamada de control) | sí |

**Audios:** no están en el repositorio (`.gitignore`) porque contienen voces de personas. Se pueden pedir a la autora.
Para reproducir todo sin ellos basta la caché de transcripciones, que sí está versionada en [cache/](cache/).

## El pipeline

**Se hace una vez:** guiones → grabación → referencias revisadas a mano → escalera de degradación
([scripts/degradar.py](scripts/degradar.py)) → transcripción de cada corrida y caché
([scripts/transcribir_corpus.py](scripts/transcribir_corpus.py), [notebooks/colab_gpu.ipynb](notebooks/colab_gpu.ipynb))
→ extracción con LLM en Colab ([scripts/extraer_llm.py](scripts/extraer_llm.py)) → métricas desde la caché
([scripts/evaluar.py](scripts/evaluar.py)).

**Se hace con cada audio nuevo:** `motor.procesar(ruta_audio, esquema)` →
1. transcripción con faster-whisper ([motor/asr.py](motor/asr.py));
2. números dichos → cifras ([motor/numeros.py](motor/numeros.py));
3. extracción de campos con reglas ([motor/extraccion_reglas.py](motor/extraccion_reglas.py)) o con Qwen
   ([motor/extraccion_llm.py](motor/extraccion_llm.py));
4. verificación literal de cada campo ([motor/verificacion.py](motor/verificacion.py));
5. solo en pedidos: validación aritmética y diagnóstico ([motor/validacion.py](motor/validacion.py)).

### Un motor, dos registros

[motor/engine.py](motor/engine.py) expone una sola función:

```python
from motor import procesar
procesar("audio/E01.mp3", "entrevista")   # Tarea 1
procesar("audio/L01.mp3", "pedido")       # Tarea 2
```

Devuelve siempre el mismo formato: `transcripcion`, `campos`, `verificacion` (qué campos están verificados),
`validacion` (solo pedidos), `dispositivo`, `segundos` y `error`. Lo único que depende del esquema es qué extractor de
campos se llama (un diccionario `EXTRACTORES`) y si se valida la aritmética. La transcripción, la normalización de
números, la verificación y el manejo de errores son el mismo código para las dos tareas, así que cambiar de modelo
(`asr.modelo` en `config.yaml`) cambia las dos tareas a la vez. No se copió el motor para la Tarea 2.

**El motor no importa ninguna librería de interfaz.** Se comprueba con:

```bash
grep -rnE "^\s*(import|from)\s+(streamlit|altair|gradio|flask)" motor/   # no debe imprimir nada
```

Es también un paso de la puerta de calidad en GitHub Actions.

### Decisiones y lo que se descartó

| Paso | Decisión | Descartado y por qué |
|---|---|---|
| Referencia | Guion corregido escuchando | Subtítulos de YouTube o salida de Whisper: evaluación circular |
| ASR | faster-whisper large-v3-turbo (multilingüe) | Modelos punteros en inglés solamente; no sirven para español |
| Precisión | se mide float16 contra int8 | Elegir sin medir si cambia el texto |
| Dispositivo | se lee de `ctranslate2` en tiempo de ejecución, VRAM con NVML | Confiar en `device="cuda"` de la configuración: la caída a CPU es silenciosa |
| Glosario | `hotwords` y `initial_prompt` medidos por separado | Agregar a las reglas los errores del ASR («hincacola»): sería ajustar al conjunto de prueba |
| Extracción | reglas y Qwen 2.5 3B local, comparados | Una API externa: los audios no salen de la organización |
| Verificación | todo valor debe estar literalmente en la transcripción | Aceptar «correcciones» del LLM aunque acierten |
| Validación | Σ cantidad × precio − promoción = total dicho | Confiar en el total dicho |
| CI | evalúa la caché; nunca transcribe | Transcribir en GitHub Actions: los runners no tienen GPU |

## Reglas de normalización

**Para comparar textos (WER, CER y verificación),** se aplica la misma regla a referencia e hipótesis
([motor/numeros.py](motor/numeros.py), `normalizar`): números dichos → cifras, minúsculas, sin tildes, sin
puntuación (se conserva el punto decimal de 6.5), espacios simples. Así «seis mil quinientos» y «6.500» no cuentan
como error.

**Números dichos en palabras:**
1. Separadores de miles del ASR fuera: «6.500», «6,500» y «6 500» → 6500; «1,5» → 1.5.
2. Una secuencia de palabras numéricas se suma por bloques: «seis mil quinientos» = 6 × 1000 + 500.
3. La secuencia se corta cuando una palabra no puede seguir a la anterior: «nueve ocho siete» son tres números (un
   teléfono dictado). «y» solo une decenas con unidades («treinta y dos»).
4. «N y medio» → N.5 («seis años y medio» → 6.5).
5. «un/uno/una» → 1, porque en un pedido «un ceviche» es una cantidad.

**Fechas:** «inmediata» se guarda como categoría; «el 13 de noviembre» y «el primero de diciembre» como fecha;
«en dos semanas» y «en un mes» se cuentan desde la fecha de la escena (29 de octubre de 2026, en `config.yaml`).

## Regla de verificación

Un campo queda `verificado` solo si su **evidencia** (el fragmento del que salió el valor) aparece literalmente en la
transcripción normalizada **y** el valor se deduce de esa evidencia con las reglas deterministas de arriba. Si el LLM
devuelve 6500 pero su cita no está en la transcripción, o la cita dice otra cosa, el campo queda `sin_verificar`
aunque el número sea correcto: un modelo que corrige lo que el ASR oyó mal y acierta es tan peligroso como uno que
inventa, porque la próxima vez corregirá y se equivocará.

## Glosario de dominio: qué hace de verdad cada mecanismo

Revisado en el código de faster-whisper 1.2.1 (`transcribe.py`, `get_prompt`):

- `hotwords` **no** modifica las probabilidades del modelo. Pone el texto del glosario en la posición de «texto
  anterior» (`<|startofprev|>`) **al inicio de cada ventana de 30 s**. No tiene efecto si se pasa `prefix`, y se recorta
  a la mitad del contexto (~223 tokens).
- `initial_prompt` usa la misma posición, pero **solo en la primera ventana**; después lo desplaza el propio texto ya
  transcrito (con `condition_on_previous_text`).

En clips de 2 a 4 minutos (5 a 8 ventanas) eso significa que `hotwords` recuerda el vocabulario durante todo el clip
e `initial_prompt` lo olvida después de los primeros 30 segundos. Por eso se miden los dos.

## Resultados

Todas las tablas se generan con `python scripts/evaluar.py && python scripts/tablas_readme.py`.

### Capa 1 · Transcripción

<!-- TRANSCRIPCION -->
| Corrida | Clips | WER | IC 95 % | CER | s / min de audio | VRAM pico (MB) | Dispositivo (leído) | GPU |
|---|---|---|---|---|---|---|---|---|
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | 10 | 0.071 | [0.059, 0.082] | 0.040 | 142.1 | — | cpu | — |
<!-- /TRANSCRIPCION -->

**Evidencia de que se usó la GPU:** la columna «Dispositivo (leído)» viene de `modelo.model.device` de ctranslate2 en
tiempo de ejecución, no de `config.yaml`, y la VRAM la mide NVML en un hilo cada 50 ms mientras transcribe. Una
corrida que hubiera caído a CPU mostraría `cpu`, sin VRAM y ~40 veces más lenta.

**¿Cambió el texto?** (pares de corridas que difieren en una sola cosa)

<!-- CAMBIOS -->
_Pendiente: requiere las corridas de Colab._
<!-- /CAMBIOS -->

**Glosario** (diferencia pareada de WER por clip; negativo = mejora)

<!-- GLOSARIO -->
_Pendiente: requiere las corridas de Colab._
<!-- /GLOSARIO -->

### Capa 2 · Registro

Exactitud por campo con intervalo de Wilson al 95 % y proporción de campos verificados.

<!-- REGISTRO -->
| Corrida | Tarea | Campo | Exactitud reglas | Verificados reglas | Error abs. reglas |
|---|---|---|---|---|---|
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | entrevista | anios_experiencia | 1.00 [0.57, 1.00] | 1.00 | 0.0 |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | entrevista | disponibilidad | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | entrevista | nivel_ingles | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | entrevista | pretension_salarial | 1.00 [0.57, 1.00] | 1.00 | 0.0 |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | entrevista | tecnologias | 0.40 [0.12, 0.77] | 1.00 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | entrevista | ultimo_puesto | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | pedido | direccion_entrega | 0.80 [0.38, 0.96] | 0.80 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | pedido | items | 0.40 [0.12, 0.77] | 1.00 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | pedido | metodo_pago | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | pedido | promocion | 1.00 [0.57, 1.00] | 0.80 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | pedido | total_dicho | 1.00 [0.57, 1.00] | 1.00 | 0.0 |

| corrida | metodo | macro_f1_ingles |
|---|---|---|
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | reglas | 1.0 |
<!-- /REGISTRO -->

### Tarea 2 · Escalera de degradación

L1 = WhatsApp (Opus 16 kbps, mono) · L2 = teléfono (300–3400 Hz, 8 kHz) · L3 = L1 + murmullo de conversaciones a
**5 dB de SNR**. La SNR se mide sobre los tramos con voz (ventanas de 30 ms por encima de −40 dB del máximo), para que
los silencios no la bajen; el script la vuelve a medir después de mezclar (`audio_degradado/L3/snr_medida.json`). Se
eligieron 5 dB porque es el ruido de un restaurante o una calle con gente hablando; el murmullo se arma con 6 clips del
propio corpus invertidos en el tiempo, para que suene a voces sin dar palabras que el ASR pueda copiar.

<!-- ESCALERA -->
_Pendiente: requiere las corridas L1–L3 de Colab._
<!-- /ESCALERA -->

### Tarea 2 · Validación aritmética: atrapados contra perdidos

Un registro está «roto» si el total dicho está mal a propósito o si el ASR o la extracción lo dañaron.

<!-- VALIDACION -->
| corrida | metodo | errores_plantados | atrapados | perdidos | registros_rotos | rotos_atrapados | rotos_perdidos | registros_sanos | falsas_alarmas | diagnosticos_evaluables | diagnosticos_correctos |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | reglas | 3 | 3 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 4 |
<!-- /VALIDACION -->

**Regla de diagnóstico.** Si el total no cuadra: (1) si el total dicho coincide exactamente con un error de cuenta
típico (olvidar la promoción, aplicar dos promociones no acumulables, descontar dos veces), se culpa al hablante;
(2) si no, y alguna cifra tiene probabilidad de palabra baja en Whisper, se culpa al ASR; (3) si no, «indeterminado».

## Limitaciones: lo que esta muestra no permite afirmar

- **Diez clips.** Cinco entrevistas × seis campos = 30 observaciones; cinco llamadas × cinco campos = 25. Alcanza para
  ver efectos grandes (que un WER de 7 % conviva con pedidos rotos) y no para estimar con precisión: los intervalos de
  confianza son anchos y están en las tablas.
- **Dos voces, un acento, un micrófono.** Todo lo grabó la misma pareja por Discord. No dice nada de otros acentos,
  de ruido real ni de llamadas telefónicas reales: L2 y L3 son simulaciones.
- **El LLM corrió una vez, con temperatura 0.** No se midió su variación entre corridas.
- **El diagnóstico se equivoca cuando un error del ASR vale lo mismo que la promoción** (en L02, la Inca Kola perdida
  y el descuento valen 10 soles).
- **Las reglas tienen falsos positivos conocidos:** cualquier tecnología mencionada entra en la lista, aunque la persona
  diga que no la domina (Go en E02) o la nombre de pasada (Excel en E01).

## Para qué NO se debe usar

Para decidir sobre personas sin que un humano lea el registro: descartar candidatos, fijar sueldos o cobrar pedidos de
forma automática. Un campo verificado solo dice que el valor está en la transcripción, no que la transcripción sea lo
que se dijo. Tampoco debe usarse para grabar a nadie sin su consentimiento.

## Cómo correrlo

```bash
pip install -r requirements.txt
streamlit run app.py                          # usa la caché; no transcribe al arrancar
python scripts/evaluar.py                     # recalcula todas las métricas desde cache/
python scripts/tablas_readme.py               # actualiza las tablas de este README
python -m motor.engine audio/L01.mp3 pedido   # el motor sobre un audio nuevo (necesita el modelo, ~1.6 GB)
```

Mediciones en GPU: abrir [notebooks/colab_gpu.ipynb](notebooks/colab_gpu.ipynb) en Colab con una T4 y «Ejecutar todas».
Configuración: [config.yaml](config.yaml) (rutas, modelos, umbrales, prompts, carta). Credenciales: `.env` (ver
[.env.example](.env.example)); ninguna es necesaria para usar la caché.

## Innovación

- **Puerta de calidad en GitHub Actions** ([.github/workflows/calidad.yml](.github/workflows/calidad.yml)): recalcula
  las métricas desde la caché y falla si el WER o la exactitud del registro bajan de los umbrales de `config.yaml`.
  No transcribe porque los runners no tienen GPU; si lo intentara, caería a CPU y tardaría horas, o fallaría.

## Herramientas de IA declaradas

- **Claude Code (Claude Opus 5.5):** ayudó a escribir el código del motor, los scripts, el notebook y la app, y a
  redactar los guiones a partir de las decisiones de la autora. La autora revisó cada pull request antes de fusionarlo.
- **Servidores MCP conectados en Claude Code:** Google Drive y Claude Docs (conectores de claude.ai). Ninguno se usó
  para el código ni para los datos de este proyecto; los audios se subieron a Drive a mano para Colab.
- **GitHub CLI (`gh`):** abrir pull requests desde la terminal.
