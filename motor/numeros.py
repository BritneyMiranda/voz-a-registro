"""Números dichos en voz alta → cifras.

Reglas (documentadas también en el README):
1. Los separadores de miles que escribe el ASR se quitan: "6.500", "6,500" y "6 500" → "6500".
   Un separador seguido de exactamente 3 dígitos es de miles; "1,5" es decimal → "1.5".
2. Una secuencia de palabras numéricas se convierte en un solo número sumando por bloques:
   "seis mil quinientos" = (6 × 1000) + 500 = 6500; "ciento doce" = 112.
3. La secuencia se corta cuando una palabra no puede continuar el número anterior:
   "nueve ocho siete" son tres números (9 8 7), igual que se dicta un teléfono o un DNI.
   "y" solo une decenas con unidades ("treinta y dos"); en cualquier otro lugar corta.
4. "N y medio" / "N y media" → N.5 ("seis y medio" → 6.5, "un año y medio" → 1.5 año).
5. "un", "uno" y "una" valen 1, porque en un pedido "un ceviche" es una cantidad.
"""
import re
import unicodedata

UNIDADES = {
    "cero": 0, "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
}
DIEZ_A_VEINTINUEVE = {
    "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciseis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
    "veintiun": 21, "veintiuno": 21, "veintiuna": 21, "veintidos": 22, "veintitres": 23,
    "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26, "veintisiete": 27,
    "veintiocho": 28, "veintinueve": 29,
}
DECENAS = {"treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
           "setenta": 70, "ochenta": 80, "noventa": 90}
CENTENAS = {
    "cien": 100, "ciento": 100, "doscientos": 200, "doscientas": 200, "trescientos": 300,
    "trescientas": 300, "cuatrocientos": 400, "cuatrocientas": 400, "quinientos": 500,
    "quinientas": 500, "seiscientos": 600, "seiscientas": 600, "setecientos": 700,
    "setecientas": 700, "ochocientos": 800, "ochocientas": 800, "novecientos": 900,
    "novecientas": 900,
}
MULTIPLICADORES = {"mil": 1000, "millon": 1_000_000, "millones": 1_000_000}

# Orden de magnitud de cada palabra: un número solo puede seguir con palabras de orden menor.
ORDEN = {**{p: 0 for p in UNIDADES}, **{p: 1 for p in DIEZ_A_VEINTINUEVE},
         **{p: 1 for p in DECENAS}, **{p: 2 for p in CENTENAS}}


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _valor(palabra: str):
    for tabla in (UNIDADES, DIEZ_A_VEINTINUEVE, DECENAS, CENTENAS):
        if palabra in tabla:
            return tabla[palabra]
    return None


def _quitar_separadores(texto: str) -> str:
    texto = re.sub(r"(?<=\d)[.,\s](?=\d{3}\b)", "", texto)    # 6.500 / 6,500 / 6 500 → 6500
    texto = re.sub(r"(?<=\d)[.,\s](?=\d{3}\b)", "", texto)    # segunda pasada: 1.000.000
    return re.sub(r"(?<=\d),(?=\d)", ".", texto)               # 1,5 → 1.5


def palabras_a_cifras(texto: str) -> str:
    """Devuelve el texto con cada número dicho en palabras reemplazado por cifras."""
    tokens = re.findall(r"\d+(?:\.\d+)?|\w+|[^\w\s]", _quitar_separadores(texto))
    salida, i = [], 0
    while i < len(tokens):
        clave = sin_tildes(tokens[i].lower())
        if _valor(clave) is None and clave not in MULTIPLICADORES:
            salida.append(tokens[i])
            i += 1
            continue
        total, bloque, ultimo_orden = 0, 0, 9
        while i < len(tokens):
            clave = sin_tildes(tokens[i].lower())
            if clave in MULTIPLICADORES:
                total += (bloque or 1) * MULTIPLICADORES[clave]
                bloque, ultimo_orden = 0, 3
                i += 1
                continue
            valor = _valor(clave)
            if valor is None:
                # "treinta y dos": la "y" solo continúa el número tras una decena exacta
                siguiente = sin_tildes(tokens[i + 1].lower()) if i + 1 < len(tokens) else ""
                if clave == "y" and bloque % 100 in DECENAS.values() and siguiente in UNIDADES:
                    i += 1
                    continue
                break
            if ORDEN[clave] >= ultimo_orden:
                break                                          # "nueve ocho": empieza otro número
            bloque += valor
            ultimo_orden = ORDEN[clave]
            i += 1
        salida.append(str(total + bloque))
    texto = " ".join(salida)
    texto = re.sub(r"(\d+)\s+(años?|anos?)\s+y\s+medi[oa]\b", r"\1.5 \2", texto, flags=re.I)
    texto = re.sub(r"(\d+)\s+y\s+medi[oa]\b", r"\1.5", texto, flags=re.I)
    return re.sub(r"\s+([,.;:!?)])", r"\1", texto)


def normalizar(texto: str) -> str:
    """Regla única para comparar textos (WER, CER y verificación literal):
    números a cifras, minúsculas, sin tildes, sin puntuación, espacios simples."""
    texto = sin_tildes(palabras_a_cifras(texto).lower())
    texto = re.sub(r"(?<!\d)\.|\.(?!\d)", " ", texto)          # conserva el punto decimal de 6.5
    texto = re.sub(r"[^\w\s.]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()
