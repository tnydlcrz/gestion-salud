from decimal import Decimal, InvalidOperation

COLORES = {
    "verde": "#0f766e",
    "rojo": "#b91c1c",
    "gris": "#94a3b8",
}


def dec(value):
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def calcular_valor(tipo_calculo, unidad, numerador, denominador):
    num = dec(numerador)
    if num is None:
        return None
    if tipo_calculo == "valor_directo":
        return num
    den = dec(denominador)
    if den is None or den == 0:
        return None
    razon = num / den
    if (unidad or "").strip() == "%":
        return (razon * Decimal("100")).quantize(Decimal("0.0001"))
    return razon.quantize(Decimal("0.0001"))


def semaforo(meta_tipo, valor, meta_min, meta_max):
    if meta_tipo == "seguimiento":
        return "gris"
    valor = dec(valor)
    if valor is None:
        return "gris"
    minimo = dec(meta_min)
    maximo = dec(meta_max)
    if meta_tipo == "minimo":
        return "gris" if minimo is None else ("verde" if valor >= minimo else "rojo")
    if meta_tipo == "maximo":
        return "gris" if maximo is None else ("verde" if valor <= maximo else "rojo")
    if meta_tipo == "rango":
        if minimo is None or maximo is None:
            return "gris"
        return "verde" if minimo <= valor <= maximo else "rojo"
    if meta_tipo == "sostener":
        if minimo is None:
            return "gris"
        if maximo is None:
            return "verde" if valor >= minimo else "rojo"
        return "verde" if minimo <= valor <= maximo else "rojo"
    return "gris"


def fmt_num(value):
    numero = dec(value)
    if numero is None:
        return ""
    if numero == numero.to_integral_value():
        return str(int(numero))
    return format(numero.normalize(), "f")


def texto_meta(meta_tipo, unidad, meta_min, meta_max):
    unidad = (unidad or "").strip()
    sufijo = f" {unidad}" if unidad else ""
    if meta_tipo == "seguimiento":
        return "En seguimiento"
    if meta_tipo == "rango":
        return f"{fmt_num(meta_min)} – {fmt_num(meta_max)}{sufijo}"
    if meta_tipo == "maximo":
        return f"≤ {fmt_num(meta_max)}{sufijo}" if meta_max is not None else None
    if meta_min is None:
        return None
    return f"≥ {fmt_num(meta_min)}{sufijo}"


def texto_nd(numerador, denominador, es_razon, es_prueba):
    n = fmt_num(numerador) if numerador is not None else "s/d"
    d = "n/a" if not es_razon else (fmt_num(denominador) if denominador is not None else "s/d")
    partes = [f"N {n}", f"D {d}"]
    if es_prueba:
        partes.append("VP")
    return " · ".join(partes)


def meta_para(metas, fecha_corte):
    if not fecha_corte or not metas:
        return None
    candidatas = [
        meta
        for meta in metas
        if meta["fecha_inicio_meta"] <= fecha_corte <= meta["fecha_fin_meta"]
    ]
    if not candidatas:
        return None
    return max(candidatas, key=lambda item: item["fecha_inicio_meta"])
