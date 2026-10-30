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
  La autora aparece en los 10 clips; la otra voz es de una persona del mismo curso, que aceptó participar (la autora
  también participó en sus grabaciones, con un guion distinto). No se la nombra aquí.

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
cada lugar donde lo grabado se apartó del guion (47 líneas cambiadas en los 10 clips) ([scripts/revisar_referencias.py](scripts/revisar_referencias.py),
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

Todas las tablas se generan con `python scripts/evaluar.py && python scripts/tablas_readme.py`. La GPU es una
Tesla T4 de Colab (15 GB); la CPU de la laptop, un Intel Core i7-1165G7.

### Lo que dicen los números

- **Modelo y precisión.** large-v3-turbo baja el WER de 9,1 % (small) a 4,0 %. int8 ocupa 1 236 MB de VRAM contra
  1 940 MB de float16, pero no es gratis: cambió el texto en 8 de 10 clips y subió el WER a 5,2 %, con intervalos que
  se solapan. Más rápido y un poco peor; para este corpus se queda float16 en GPU.
- **CPU contra GPU, en la misma máquina de Colab:** E01 tardó 221 s en CPU y 7 s en la T4 (≈ 30 veces), y el texto
  cambió en 1 de los 2 clips comparados.
- **Glosario.** `initial_prompt` no cambia nada (Δ WER +0,0004, IC que incluye el cero). `hotwords` sí corrige nombres
  propios (por fin escribe «Inca Kola»), pero **empeora el WER de 4,0 % a 22,4 %**: con el glosario repetido en cada
  ventana, Whisper entra en bucles («el arroz con arroz con arroz con…» en L02) y se salta frases enteras (74 palabras
  borradas en E04). Más contexto no es mejor contexto.
- **¿Se puede saber si el registro sirve mirando solo el WER? No.** Con el mismo modelo (small, audio original),
  **L03 tiene WER de 12,2 % y sus 5 campos correctos**, y **L02 tiene WER de 7,9 % y solo 2 de 5**: sus pocos errores
  caen en «Inca Kola», en un plato y en la dirección. En las 100 combinaciones clip × corrida, la correlación entre
  WER y exactitud del registro es −0,63: el WER ayuda, pero no alcanza. Quien reporta solo WER está reportando cuántas
  palabras se oyeron mal, no si los datos que importan están bien.
- **Asimetría entre tipos de campo.** El inglés (3 clases) sale bien en todos los niveles menos L3: le basta con oír
  una de pocas palabras. Las cifras y los nombres propios son lo primero que se rompe («dos ceviches» → «12 biches»,
  «Jirón» → «Irón»), y un número con un dígito mal es un registro equivocado, no uno aproximado.
- **Reglas contra Qwen 2.5 3B (prompt v2), audio original.** Las reglas ganan en casi todo: años 100 % contra 40 %
  (Qwen inventa medios años: 4,5 donde se dijo «cuatro»), disponibilidad 100 % contra 20 % (pone «inmediata» citando
  «desde el viernes 13 de noviembre»), inglés F1 macro 1,00 contra 0,78, ítems del pedido 40 % contra 20 %. Qwen gana
  en tecnologías (60 % contra 40 %) porque entiende que Go «no lo pondría como fortaleza» y que el Excel de E01 era de
  pasada, justo donde las reglas fallan por diseño.
- **La verificación hace su trabajo.** De los 17 campos que Qwen sacó mal en L0, **13 quedaron `sin_verificar`**: su
  cita no estaba en la transcripción o no respaldaba el valor. Se escaparon 4, cuya cita sí estaba (por ejemplo
  «Piespark», como Whisper oyó «PySpark»). El costo: 7 campos correctos de Qwen también quedaron sin verificar,
  porque citó parafraseando. Un campo verificado no es un campo correcto, pero un campo sin verificar es una alarma
  que se puede atender.
- **La referencia importa.** Antes de corregir la referencia escuchando, el WER era 6,0 %; después, 4,0 %. Un tercio
  de lo que parecía error del ASR eran palabras que sí se dijeron pero no estaban en el guion.

### Capa 1 · Transcripción

<!-- TRANSCRIPCION -->
| Corrida | Clips | WER | IC 95 % | CER | s / min de audio | VRAM pico (MB) | Dispositivo (leído) | GPU |
|---|---|---|---|---|---|---|---|---|
| L0_large-v3-turbo_float16_cuda_glosario-hotwords | 10 | 0.224 | [0.157, 0.303] | 0.182 | 3.2 | 2518 | cuda | Tesla T4 |
| L0_large-v3-turbo_float16_cuda_glosario-initial_prompt | 10 | 0.040 | [0.024, 0.059] | 0.025 | 2.5 | 2486 | cuda | Tesla T4 |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | 10 | 0.040 | [0.028, 0.054] | 0.017 | 2.2 | 2518 | cuda | Tesla T4 |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | 10 | 0.047 | [0.033, 0.060] | 0.023 | 142.1 | — | cpu | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno_colab | 2 | 0.028 | [0.017, 0.040] | 0.012 | 65.2 | 450 | cpu | — |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | 10 | 0.052 | [0.033, 0.072] | 0.030 | 2.5 | 1686 | cuda | Tesla T4 |
| L0_small_float16_cuda_glosario-ninguno | 10 | 0.091 | [0.068, 0.114] | 0.033 | 1.6 | 1302 | cuda | Tesla T4 |
| L0_small_int8_cuda_glosario-ninguno | 10 | 0.092 | [0.070, 0.113] | 0.031 | 1.7 | 1046 | cuda | Tesla T4 |
| L1_large-v3-turbo_float16_cuda_glosario-ninguno | 10 | 0.049 | [0.035, 0.062] | 0.028 | 2.9 | 2518 | cuda | Tesla T4 |
| L2_large-v3-turbo_float16_cuda_glosario-ninguno | 10 | 0.054 | [0.042, 0.065] | 0.032 | 2.8 | 2518 | cuda | Tesla T4 |
| L3_large-v3-turbo_float16_cuda_glosario-ninguno | 10 | 0.212 | [0.165, 0.270] | 0.129 | 2.9 | 2550 | cuda | Tesla T4 |
<!-- /TRANSCRIPCION -->

**Evidencia de que se usó la GPU:** la columna «Dispositivo (leído)» viene de `modelo.model.device` de ctranslate2 en
tiempo de ejecución, no de `config.yaml`, y la VRAM la mide NVML en un hilo cada 50 ms mientras transcribe. Una
corrida que hubiera caído a CPU mostraría `cpu`, sin VRAM y ~40 veces más lenta.

**¿Cambió el texto?** (pares de corridas que difieren en una sola cosa)

<!-- CAMBIOS -->
| A | B | Clips | Clips con texto distinto | WER entre A y B |
|---|---|---|---|---|
| L0_large-v3-turbo_float16_cuda_glosario-hotwords | L0_large-v3-turbo_float16_cuda_glosario-initial_prompt | 10 | 10 | 0.199 |
| L0_large-v3-turbo_float16_cuda_glosario-hotwords | L0_large-v3-turbo_float16_cuda_glosario-ninguno | 10 | 10 | 0.203 |
| L0_large-v3-turbo_float16_cuda_glosario-initial_prompt | L0_large-v3-turbo_float16_cuda_glosario-ninguno | 10 | 10 | 0.028 |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | L0_large-v3-turbo_int8_cuda_glosario-ninguno | 10 | 8 | 0.017 |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | L0_small_float16_cuda_glosario-ninguno | 10 | 10 | 0.080 |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | L0_large-v3-turbo_int8_cuda_glosario-ninguno | 10 | 9 | 0.016 |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno_colab | L0_large-v3-turbo_int8_cuda_glosario-ninguno | 2 | 1 | 0.011 |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | L0_small_int8_cuda_glosario-ninguno | 10 | 10 | 0.086 |
| L0_small_float16_cuda_glosario-ninguno | L0_small_int8_cuda_glosario-ninguno | 10 | 10 | 0.027 |
<!-- /CAMBIOS -->

**Glosario** (diferencia pareada de WER por clip; negativo = mejora)

<!-- GLOSARIO -->
| Sin glosario | Con glosario | Clips | Δ WER (con − sin) | IC 95 % (bootstrap pareado) |
|---|---|---|---|---|
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | L0_large-v3-turbo_float16_cuda_glosario-hotwords | 10 | +0.184 | [0.120, 0.261] |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | L0_large-v3-turbo_float16_cuda_glosario-initial_prompt | 10 | +0.000 | [-0.010, 0.009] |
<!-- /GLOSARIO -->

### Capa 2 · Registro

Exactitud por campo con intervalo de Wilson al 95 % y proporción de campos verificados.

<!-- REGISTRO -->
| Corrida | Tarea | Campo | Exactitud llm | Verificados llm | Error abs. llm | Exactitud reglas | Verificados reglas | Error abs. reglas |
|---|---|---|---|---|---|---|---|---|
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | entrevista | anios_experiencia | 0.40 [0.12, 0.77] | 0.40 | 0.3 | 1.00 [0.57, 1.00] | 1.00 | 0.0 |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | entrevista | disponibilidad | 0.20 [0.04, 0.62] | 0.20 | — | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | entrevista | nivel_ingles | 0.80 [0.38, 0.96] | 0.60 | — | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | entrevista | pretension_salarial | 1.00 [0.57, 1.00] | 1.00 | 0.0 | 1.00 [0.57, 1.00] | 1.00 | 0.0 |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | entrevista | tecnologias | 0.60 [0.23, 0.88] | 0.80 | — | 0.40 [0.12, 0.77] | 1.00 | — |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | entrevista | ultimo_puesto | 0.80 [0.38, 0.96] | 1.00 | — | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | pedido | direccion_entrega | 1.00 [0.57, 1.00] | 0.60 | — | 0.80 [0.38, 0.96] | 0.80 | — |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | pedido | items | 0.20 [0.04, 0.62] | 0.40 | — | 0.40 [0.12, 0.77] | 1.00 | — |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | pedido | metodo_pago | 1.00 [0.57, 1.00] | 1.00 | — | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | pedido | promocion | 0.60 [0.23, 0.88] | 0.20 | — | 1.00 [0.57, 1.00] | 0.80 | — |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | pedido | total_dicho | 1.00 [0.57, 1.00] | 0.80 | 0.0 | 1.00 [0.57, 1.00] | 1.00 | 0.0 |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | entrevista | anios_experiencia | — | — | — | 1.00 [0.57, 1.00] | 1.00 | 0.0 |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | entrevista | disponibilidad | — | — | — | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | entrevista | nivel_ingles | — | — | — | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | entrevista | pretension_salarial | — | — | — | 1.00 [0.57, 1.00] | 1.00 | 0.0 |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | entrevista | tecnologias | — | — | — | 0.40 [0.12, 0.77] | 1.00 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | entrevista | ultimo_puesto | — | — | — | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | pedido | direccion_entrega | — | — | — | 0.80 [0.38, 0.96] | 0.80 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | pedido | items | — | — | — | 0.40 [0.12, 0.77] | 1.00 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | pedido | metodo_pago | — | — | — | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | pedido | promocion | — | — | — | 1.00 [0.57, 1.00] | 0.80 | — |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | pedido | total_dicho | — | — | — | 1.00 [0.57, 1.00] | 1.00 | 0.0 |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | entrevista | anios_experiencia | — | — | — | 1.00 [0.57, 1.00] | 1.00 | 0.0 |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | entrevista | disponibilidad | — | — | — | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | entrevista | nivel_ingles | — | — | — | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | entrevista | pretension_salarial | — | — | — | 1.00 [0.57, 1.00] | 1.00 | 0.0 |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | entrevista | tecnologias | — | — | — | 0.40 [0.12, 0.77] | 1.00 | — |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | entrevista | ultimo_puesto | — | — | — | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | pedido | direccion_entrega | — | — | — | 0.80 [0.38, 0.96] | 0.80 | — |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | pedido | items | — | — | — | 0.40 [0.12, 0.77] | 1.00 | — |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | pedido | metodo_pago | — | — | — | 1.00 [0.57, 1.00] | 1.00 | — |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | pedido | promocion | — | — | — | 1.00 [0.57, 1.00] | 0.80 | — |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | pedido | total_dicho | — | — | — | 1.00 [0.57, 1.00] | 1.00 | 0.0 |

| corrida | metodo | macro_f1_ingles |
|---|---|---|
| L0_large-v3-turbo_float16_cuda_glosario-hotwords | reglas | 0.889 |
| L0_large-v3-turbo_float16_cuda_glosario-initial_prompt | reglas | 1.0 |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | llm | 0.778 |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | reglas | 1.0 |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | reglas | 1.0 |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno_colab | reglas | 1.0 |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | reglas | 1.0 |
| L0_small_float16_cuda_glosario-ninguno | reglas | 1.0 |
| L0_small_int8_cuda_glosario-ninguno | reglas | 1.0 |
| L1_large-v3-turbo_float16_cuda_glosario-ninguno | llm | 0.778 |
| L1_large-v3-turbo_float16_cuda_glosario-ninguno | reglas | 1.0 |
| L2_large-v3-turbo_float16_cuda_glosario-ninguno | llm | 0.778 |
| L2_large-v3-turbo_float16_cuda_glosario-ninguno | reglas | 1.0 |
| L3_large-v3-turbo_float16_cuda_glosario-ninguno | llm | 0.822 |
| L3_large-v3-turbo_float16_cuda_glosario-ninguno | reglas | 0.889 |
<!-- /REGISTRO -->

### Tarea 2 · Escalera de degradación

L1 = WhatsApp (Opus 16 kbps, mono) · L2 = teléfono (300–3400 Hz, 8 kHz) · L3 = L1 + murmullo de conversaciones a
**5 dB de SNR**. La SNR se mide sobre los tramos con voz (ventanas de 30 ms por encima de −40 dB del máximo), para que
los silencios no la bajen; el script la vuelve a medir después de mezclar (`audio_degradado/L3/snr_medida.json`). Se
eligieron 5 dB porque es el ruido de un restaurante o una calle con gente hablando; el murmullo se arma con 6 clips del
propio corpus invertidos en el tiempo, para que suene a voces sin dar palabras que el ASR pueda copiar.

<!-- ESCALERA -->
| nivel | WER entrevista | WER pedido | campos entrevista (llm) | campos entrevista (reglas) | campos pedido (llm) | campos pedido (reglas) |
|---|---|---|---|---|---|---|
| L0 | 0.028 | 0.052 | 0.633 | 0.9 | 0.76 | 0.84 |
| L1 | 0.034 | 0.063 | 0.633 | 0.9 | 0.8 | 0.92 |
| L2 | 0.042 | 0.065 | 0.667 | 0.9 | 0.76 | 0.84 |
| L3 | 0.156 | 0.269 | 0.5 | 0.6 | 0.64 | 0.6 |
<!-- /ESCALERA -->

### Tarea 2 · Validación aritmética: atrapados contra perdidos

Un registro está «roto» si el total dicho está mal a propósito o si el ASR o la extracción lo dañaron.

<!-- VALIDACION -->
| corrida | metodo | errores_plantados | atrapados | perdidos | registros_rotos | rotos_atrapados | rotos_perdidos | registros_sanos | falsas_alarmas | diagnosticos_evaluables | diagnosticos_correctos |
|---|---|---|---|---|---|---|---|---|---|---|---|
| L0_large-v3-turbo_float16_cuda_glosario-hotwords | reglas | 3 | 3 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 5 |
| L0_large-v3-turbo_float16_cuda_glosario-initial_prompt | reglas | 3 | 3 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 5 |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | llm | 3 | 2 | 1 | 5 | 3 | 2 | 0 | 0 | 3 | 3 |
| L0_large-v3-turbo_float16_cuda_glosario-ninguno | reglas | 3 | 3 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 4 |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno | reglas | 3 | 3 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 4 |
| L0_large-v3-turbo_int8_cpu_glosario-ninguno_colab | reglas | 1 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 1 |
| L0_large-v3-turbo_int8_cuda_glosario-ninguno | reglas | 3 | 3 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 4 |
| L0_small_float16_cuda_glosario-ninguno | reglas | 3 | 3 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 5 |
| L0_small_int8_cuda_glosario-ninguno | reglas | 3 | 3 | 0 | 4 | 4 | 0 | 1 | 0 | 4 | 4 |
| L1_large-v3-turbo_float16_cuda_glosario-ninguno | llm | 3 | 2 | 1 | 4 | 2 | 2 | 1 | 0 | 2 | 2 |
| L1_large-v3-turbo_float16_cuda_glosario-ninguno | reglas | 3 | 3 | 0 | 4 | 4 | 0 | 1 | 0 | 4 | 3 |
| L2_large-v3-turbo_float16_cuda_glosario-ninguno | llm | 3 | 2 | 1 | 5 | 3 | 2 | 0 | 0 | 3 | 3 |
| L2_large-v3-turbo_float16_cuda_glosario-ninguno | reglas | 3 | 3 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 4 |
| L3_large-v3-turbo_float16_cuda_glosario-ninguno | llm | 3 | 3 | 0 | 5 | 4 | 1 | 0 | 0 | 4 | 3 |
| L3_large-v3-turbo_float16_cuda_glosario-ninguno | reglas | 3 | 3 | 0 | 5 | 5 | 0 | 0 | 0 | 5 | 5 |
<!-- /VALIDACION -->

**Regla de diagnóstico.** Si el total no cuadra: (1) si el total dicho coincide exactamente con un error de cuenta
típico (olvidar la promoción, aplicar dos promociones no acumulables, descontar dos veces), se culpa al hablante;
(2) si no, y alguna cifra tiene probabilidad de palabra baja en Whisper, se culpa al ASR; (3) si no, «indeterminado».

## Limitaciones: lo que esta muestra no permite afirmar

- **Diez clips.** Cinco entrevistas × seis campos = 30 observaciones; cinco llamadas × cinco campos = 25. Alcanza para
  ver efectos grandes (que un WER de 4 % conviva con pedidos rotos) y no para estimar con precisión: los intervalos de
  confianza son anchos y están en las tablas.
- **Dos voces, un acento, un micrófono.** Todo lo grabó la misma pareja por Discord. No dice nada de otros acentos,
  de ruido real ni de llamadas telefónicas reales: L2 y L3 son simulaciones.
- **El LLM corrió una vez, con temperatura 0.** No se midió su variación entre corridas.
- **El primer prompt de Qwen falló.** Con el prompt v1 (claves descritas, sin plantilla), Qwen 2.5 3B devolvió una
  lista sin claves en las 20 respuestas de entrevistas y en 1 de 20 pedidos: el registro quedó vacío. Esas respuestas
  están en [cache/extracciones_llm_v1/](cache/extracciones_llm_v1/). La comparación reglas contra LLM usa el prompt v2,
  que da la plantilla JSON exacta. Aun en v1 se ve el riesgo que la verificación atrapa: el modelo puso disponibilidad
  «inmediata» citando una frase que dice «desde el viernes 13 de noviembre», y 4 años de experiencia citando
  «son cuatro analistas».
- **La referencia se revisó escuchando los lugares donde Whisper y el guion diferían** (135, con prioridad en los 32
  que tocan números o campos). Si Whisper y el guion coincidían en algo que no se dijo, ese error no se detectó.
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
