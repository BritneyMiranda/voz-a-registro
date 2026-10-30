"""Extracción con reglas (expresiones regulares) sobre el texto normalizado.

Cada función devuelve (campos, evidencias): la evidencia de un campo es el fragmento del texto
normalizado del que sale el valor. La verificación (verificacion.py) exige que ese fragmento
exista literalmente en la transcripción.
"""
import re
from datetime import date, timedelta

from .numeros import normalizar, palabras_a_cifras, sin_tildes

MESES = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
     "septiembre", "octubre", "noviembre", "diciembre"], start=1)}
MESES["setiembre"] = 9


def _sumar_meses(d: date, n: int) -> date:
    mes = d.month - 1 + n
    anio, mes = d.year + mes // 12, mes % 12 + 1
    dias = [31, 29 if anio % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mes - 1]
    return date(anio, mes, min(d.day, dias))


def resolver_fecha(expresion: str, hoy: date):
    """Convierte una expresión de disponibilidad (ya normalizada) en 'inmediata' o fecha ISO."""
    e = expresion
    if re.search(r"\binmediat|\bde inmediato\b|\bya mismo\b", e):
        return "inmediata"
    m = re.search(r"\b(\d{1,2}|primero) de (" + "|".join(MESES) + r")\b", e)
    if m:
        dia = 1 if m.group(1) == "primero" else int(m.group(1))
        d = date(hoy.year, MESES[m.group(2)], dia)
        return (d if d >= hoy else date(hoy.year + 1, d.month, d.day)).isoformat()
    m = re.search(r"\ben (\d+) (dias?|semanas?|mes|meses)\b", e)
    if m:
        n, unidad = int(m.group(1)), m.group(2)
        if unidad.startswith("dia"):
            return (hoy + timedelta(days=n)).isoformat()
        if unidad.startswith("semana"):
            return (hoy + timedelta(weeks=n)).isoformat()
        return _sumar_meses(hoy, n).isoformat()
    return None


def con_puntuacion(texto: str) -> str:
    """Como `normalizar`, pero conserva la puntuación: sirve para no cruzar de una frase a otra."""
    return sin_tildes(palabras_a_cifras(texto).lower())


def _ventanas_tras(texto, patron, n_palabras):
    """Fragmentos de n palabras que empiezan en cada aparición de `patron`."""
    for m in re.finditer(patron, texto):
        yield m.start(), " ".join(texto[m.start():].split()[:n_palabras])


# ---------------------------------------------------------------- entrevista

def extraer_entrevista(transcripcion: str, cfg: dict):
    t = normalizar(transcripcion)
    ce, ventana = cfg["entrevista"], cfg["extraccion"]["ventana_palabras"]
    hoy = date.fromisoformat(cfg["fecha_escena"])
    campos, evid = {}, {}

    # años: la última mención «N años» dentro de la ventana que abre la pregunta por la experiencia;
    # así «siete años… bueno, son 6.5 años» se queda con la corrección.
    campos["anios_experiencia"] = evid["anios_experiencia"] = None
    for _, frag in _ventanas_tras(t, r"\b(experiencia|llevas|trayectoria|anos en)\b", ventana // 2):
        menciones = list(re.finditer(r"\b(\d+(?:\.5)?) anos?\b", frag))
        if menciones:
            campos["anios_experiencia"] = float(menciones[-1].group(1))
            evid["anios_experiencia"] = menciones[-1].group(0)
            break

    # último puesto: frases que empiezan con una palabra de cargo, sin cruzar la puntuación; gana la que
    # va precedida por una marca de cargo actual («mi último cargo fue», «soy», «formalmente»); empate → la última.
    tp = con_puntuacion(transcripcion)
    cargos = "|".join(ce["palabras_cargo"])
    mejor = None
    for m in re.finditer(rf"\b(?:{cargos})\b(?:[ ]+(?!en\b|y\b|desde\b|que\b|a\b|ahi\b|con\b)\w+){{0,4}}", tp):
        antes = " ".join(normalizar(tp[:m.start()]).split()[-6:])
        puntos = 3 if any(marca in antes for marca in ce["marcas_cargo_actual"]) else 0
        if mejor is None or puntos >= mejor[0]:
            mejor = (puntos, m.group(0))
    campos["ultimo_puesto"] = evid["ultimo_puesto"] = mejor[1] if mejor else None

    # tecnologías: cualquier alias del glosario que aparezca como palabra completa
    encontradas, citas = [], []
    for canonico, alias in ce["tecnologias"].items():
        for a in alias:
            if re.search(rf"\b{re.escape(a)}\b", t):
                encontradas.append(canonico)
                citas.append(a)
                break
    campos["tecnologias"], evid["tecnologias"] = encontradas, citas

    # pretensión: la primera cifra entre salario_min y salario_max después de hablar de dinero,
    # descartando lo que gana hoy («gano 8000»), los rangos («entre 7 y 8000») y los años («en 2021»).
    campos["pretension_salarial"] = evid["pretension_salarial"] = None
    m0 = re.search(r"\b(economico|expectativa|pretension|salarial|pidiendo|buscaria|buscando)\b", t)
    if m0:
        for m in re.finditer(r"\b\d+\b", t[m0.start():]):
            valor = int(m.group(0))
            ini = m0.start() + m.start()
            antes = " ".join(t[:ini].split()[-3:])
            if not ce["salario_min"] <= valor <= ce["salario_max"]:
                continue
            if re.search(r"\b(gano|ganando|ganaba)\b", antes) or re.search(r"\bentre( \d+ y)?$", antes):
                continue                                       # lo que gana hoy y los extremos de un rango
            if 1990 <= valor <= 2035 and re.search(r"\b(en|de|desde|del)$", antes):
                continue
            despues = " ".join(t[ini:].split()[1:4])
            moneda = "USD" if re.search(r"\b(dolares|usd)\b", despues) else "PEN"
            campos["pretension_salarial"] = {"monto": valor, "moneda": moneda}
            evid["pretension_salarial"] = " ".join(t[ini:].split()[:2]) if moneda == "USD" else m.group(0)
            break

    # disponibilidad: la primera expresión de fecha después de preguntar cuándo empieza
    campos["disponibilidad"] = evid["disponibilidad"] = None
    patron_fecha = (r"\binmediat\w*|\bde inmediato\b|\b(?:\d{1,2}|primero) de (?:"
                    + "|".join(MESES) + r")\b|\ben \d+ (?:dias?|semanas?|mes|meses)\b")
    inicios = [ini for ini, _ in _ventanas_tras(t, r"\b(empezar|incorporarte|incorporarse|disponibilidad|comenzar)\b", 1)]
    for ini in inicios or [0]:                                 # si el ASR se comió la pregunta, todo el texto
        m = re.search(patron_fecha, t[ini:])
        if m:
            campos["disponibilidad"] = resolver_fecha(m.group(0), hoy)
            evid["disponibilidad"] = m.group(0)
            break

    # inglés: el primer nivel dicho después de la última mención de «inglés»; si ahí no hay,
    # se prueba con la mención anterior (el entrevistador puede volver a decir «inglés» después).
    campos["nivel_ingles"] = evid["nivel_ingles"] = None
    niveles = {alias: nivel for nivel, aliases in ce["niveles_ingles"].items() for alias in aliases}
    patron_nivel = r"\b(" + "|".join(sorted(niveles, key=len, reverse=True)) + r")\b"
    for m in reversed(list(re.finditer(r"\bingles\b", t))):
        frag = " ".join(t[m.end():].split()[:ventana])
        n = re.search(patron_nivel, frag)
        if n:
            campos["nivel_ingles"], evid["nivel_ingles"] = niveles[n.group(1)], n.group(1)
            break
    return campos, evid


# ---------------------------------------------------------------- pedido

def _patron(lista):
    return "(?:" + "|".join(lista) + ")"


def extraer_pedido(transcripcion: str, cfg: dict):
    t = normalizar(transcripcion)
    tp = con_puntuacion(transcripcion)
    cp = cfg["pedido"]
    campos, evid = {}, {}

    # items: cada «N producto [tamaño]» actualiza el pedido (gana la última mención);
    # «quítele las N X» lo borra y «mejor cámbialo» borra el último producto agregado.
    # Se busca en el texto con puntuación: en «personal, 29; ceviche» el 29 es un precio, no una cantidad.
    eventos = []
    tamanos = "|".join(rf"(?P<t_{i}>{_patron(a)})" for i, a in enumerate(cp["alias_tamanos"].values()))
    for producto, alias in cp["alias_productos"].items():
        p = rf"\b(?P<n>\d+)[ ]+(?:(?:{tamanos.replace('?P<t_', '?P<a_')})[ ]+de[ ]+)?" \
            rf"(?P<prod>{_patron(alias)})\b(?:,?(?:[ ]+(?:el|la|los|las|de)){{0,3}}[ ]+(?:{tamanos})\b)?"
        for m in re.finditer(p, tp):
            if int(m.group("n")) <= cp["cantidad_maxima"]:
                eventos.append((m.start(), producto, m))
    for m in re.finditer(r"\b" + _patron(cp["marcas_cambiar"]) + r"\b", tp):
        eventos.append((m.start(), "__cambiar__", m))
    eventos.sort(key=lambda e: e[0])

    nombres_tam = list(cp["alias_tamanos"])
    pedido, orden, citas, explicito = {}, [], {}, {}
    for ini, producto, m in eventos:
        if producto == "__cambiar__":
            if orden:
                pedido.pop(orden.pop(), None)
            continue
        tam = None
        for i, nombre in enumerate(nombres_tam):
            if m.groupdict().get(f"t_{i}") or m.groupdict().get(f"a_{i}"):
                tam = nombre if nombre in cp["carta"][producto] else None
        previas = [k for k in pedido if k[0] == producto]
        if tam is None:                                        # sin tamaño: el que ya tenía ese producto
            clave = previas[-1] if previas else (producto, cp["tamano_por_defecto"][producto])
        else:
            clave = (producto, tam)
            for k in previas:                                  # el tamaño dicho reemplaza al supuesto
                if not explicito.get(k) and k != clave:
                    pedido.pop(k)
                    orden = [o for o in orden if o != k]
        antes = " ".join(normalizar(tp[:ini]).split()[-3:])
        if re.search(r"\b" + _patron(cp["marcas_quitar"]) + r"\b", antes):
            pedido.pop(clave, None)
            orden = [k for k in orden if k != clave]
            continue
        pedido[clave] = int(m.group("n"))
        citas[clave] = m.group(0)
        explicito[clave] = explicito.get(clave, False) or tam is not None
        orden = [k for k in orden if k != clave] + [clave]
    campos["items"] = [{"producto": p, "tamano": tam, "cantidad": n,
                        "precio_unitario": cp["carta"][p][tam]}
                       for (p, tam), n in pedido.items() if n > 0]
    evid["items"] = [citas[k] for k in pedido if pedido[k] > 0]

    # promoción: ninguna si se dice que no hay; si el vendedor elige una («le dejo el 2 por 1»), esa;
    # si no, la última mencionada.
    campos["promocion"] = evid["promocion"] = None
    if not re.search(_patron(cp["marcas_sin_promocion"]), t):
        candidatas = []
        for clave, promo in cp["promociones"].items():
            for m in re.finditer(promo["patron"], t):
                elegida = re.search(_patron(cp["marcas_promocion_elegida"]) + r"\s*$",
                                    " ".join(t[:m.start()].split()[-3:]))
                candidatas.append((bool(elegida), m.start(), clave, m.group(0)))
        if candidatas:
            _, _, clave, cita = max(candidatas)
            campos["promocion"], evid["promocion"] = clave, cita

    # dirección: desde la primera palabra de inicio de dirección hasta el siguiente punto
    campos["direccion_entrega"] = evid["direccion_entrega"] = None
    crudo = sin_tildes(transcripcion.lower())
    m = re.search(r"\b" + _patron(cp["inicio_direccion"]) + r"\b[^.?!]*", crudo)
    if m:
        campos["direccion_entrega"] = normalizar(m.group(0))
        evid["direccion_entrega"] = campos["direccion_entrega"]

    # pago: la primera palabra de pago después de que se pregunta cómo pagará
    campos["metodo_pago"] = evid["metodo_pago"] = None
    ini = max((m.start() for m in re.finditer(r"\b(paga|pagar|pago)\b", t)), default=0)
    m0 = re.search(r"\b(como (va a )?paga\w*|forma de pago)\b", t)
    ini = m0.start() if m0 else ini
    alias_pago = {a: k for k, v in cp["pagos"].items() for a in v}
    m = re.search(r"\b(" + "|".join(alias_pago) + r")\b", t[ini:])
    if m:
        campos["metodo_pago"], evid["metodo_pago"] = alias_pago[m.group(1)], m.group(1)

    # total: la última cifra de la oración donde se dice «total» (hasta 8 palabras, sin pasar el punto);
    # «sería de cincuenta, ciento doce» es quien habla corrigiéndose, y vale lo último (como en los platos),
    # pero «…114 soles. En 35 a 40 minutos» ya es otra oración
    campos["total_dicho"] = evid["total_dicho"] = None
    for m in re.finditer(r"\b" + _patron(cp["palabras_total"]) + r"\b((?:[^\S\n]*[^\s.?!]+){0,8})", tp):
        cifras = re.findall(r"\b\d+(?:\.\d+)?\b", m.group(1))
        if cifras:
            campos["total_dicho"], evid["total_dicho"] = float(cifras[-1]), cifras[-1]
    return campos, evid
