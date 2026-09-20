from decimal import Decimal, InvalidOperation

from .models import IndicadorVersion, Medicion


def _dec(value):
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError):
        return None


def calcular_valor(version, numerador, denominador):
    num = _dec(numerador)
    if num is None:
        return None
    if version.tipo_calculo == IndicadorVersion.TipoCalculo.VALOR_DIRECTO:
        return num
    den = _dec(denominador)
    if den is None or den == 0:
        return None
    razon = num / den
    if version.unidad_resultado.strip() == "%":
        return (razon * Decimal("100")).quantize(Decimal("0.0001"))
    return razon.quantize(Decimal("0.0001"))


def semaforo(version, valor, meta):
    if version.meta_tipo == IndicadorVersion.MetaTipo.SEGUIMIENTO:
        return "gris"
    valor = _dec(valor)
    if valor is None or meta is None:
        return "gris"

    minimo = _dec(meta.meta_min)
    maximo = _dec(meta.meta_max)

    if version.meta_tipo == IndicadorVersion.MetaTipo.MINIMO:
        if minimo is None:
            return "gris"
        return "verde" if valor >= minimo else "rojo"

    if version.meta_tipo == IndicadorVersion.MetaTipo.MAXIMO:
        if maximo is None:
            return "gris"
        return "verde" if valor <= maximo else "rojo"

    if version.meta_tipo == IndicadorVersion.MetaTipo.RANGO:
        if minimo is None or maximo is None:
            return "gris"
        return "verde" if minimo <= valor <= maximo else "rojo"

    if version.meta_tipo == IndicadorVersion.MetaTipo.SOSTENER:
        if minimo is None:
            return "gris"
        if maximo is None:
            return "verde" if valor >= minimo else "rojo"
        return "verde" if minimo <= valor <= maximo else "rojo"

    return "gris"


COLORES_SEMAFORO = {
    "verde": "#0f766e",
    "rojo": "#b91c1c",
    "gris": "#94a3b8",
}


def _fmt_num(value):
    numero = _dec(value)
    if numero is None:
        return ""
    if numero == numero.to_integral_value():
        return str(int(numero))
    return format(numero.normalize(), "f")


def texto_meta(version, meta):
    if not version:
        return None
    unidad = (version.unidad_resultado or "").strip()
    sufijo = f" {unidad}" if unidad else ""
    if version.meta_tipo == IndicadorVersion.MetaTipo.SEGUIMIENTO:
        return "En seguimiento"
    if not meta:
        return None
    if version.meta_tipo == IndicadorVersion.MetaTipo.RANGO:
        return f"{_fmt_num(meta.meta_min)} – {_fmt_num(meta.meta_max)}{sufijo}"
    if version.meta_tipo == IndicadorVersion.MetaTipo.MAXIMO:
        return f"≤ {_fmt_num(meta.meta_max)}{sufijo}"
    return f"≥ {_fmt_num(meta.meta_min)}{sufijo}"


def texto_componente(valor, aplica=True):
    if not aplica:
        return "n/a"
    if valor is None:
        return "s/d"
    return _fmt_num(valor)


def texto_nd(medicion, version):
    es_razon = bool(version and version.tipo_calculo == IndicadorVersion.TipoCalculo.RAZON)
    partes = [
        f"N {texto_componente(medicion.numerador_valor)}",
        f"D {texto_componente(medicion.denominador_valor, aplica=es_razon)}",
    ]
    if medicion.es_prueba:
        partes.append("VP")
    return " · ".join(partes)


def serie_desde_mediciones(version, mediciones):
    labels = []
    values = []
    colors = []
    detalles = []
    es_razon = bool(version and version.tipo_calculo == IndicadorVersion.TipoCalculo.RAZON)
    for medicion in mediciones:
        labels.append(medicion.periodo.label)
        valor = float(medicion.valor_calculado) if medicion.valor_calculado is not None else None
        values.append(valor)
        color = semaforo(version, medicion.valor_calculado, medicion.meta_aplicable())
        colors.append(COLORES_SEMAFORO[color])
        detalles.append(
            {
                "n": texto_componente(medicion.numerador_valor),
                "d": texto_componente(medicion.denominador_valor, aplica=es_razon),
                "vp": bool(medicion.es_prueba),
            }
        )
    return {"labels": labels, "values": values, "colors": colors, "detalles": detalles}


def serie_chart(indicador):
    version = indicador.version_vigente()
    if not version:
        return {"labels": [], "values": [], "colors": [], "detalles": []}
    mediciones = version.mediciones.filter(estado=Medicion.Estado.PUBLICADO).select_related(
        "periodo", "indicador_version"
    ).prefetch_related("indicador_version__metas")
    return serie_desde_mediciones(version, mediciones)


def ultima_medicion_publicada(indicador):
    version = indicador.version_vigente()
    if not version:
        return None
    return (
        version.mediciones.filter(estado="publicado")
        .select_related("periodo", "indicador_version")
        .order_by("-periodo__fecha_fin")
        .first()
    )


def resumen_area(area):
    indicadores = list(
        area.indicadores.filter(activo=True).select_related("dimension", "area")
    )
    verdes = rojos = grises = 0
    filas = []
    for indicador in indicadores:
        version = indicador.version_vigente()
        medicion = ultima_medicion_publicada(indicador)
        color = medicion.semaforo() if medicion else "gris"
        if color == "verde":
            verdes += 1
        elif color == "rojo":
            rojos += 1
        else:
            grises += 1
        meta = None
        if medicion:
            meta = medicion.meta_aplicable()
        elif version:
            meta = version.metas.order_by("-fecha_inicio_meta").first()
        filas.append({
            "indicador": indicador,
            "medicion": medicion,
            "semaforo": color,
            "meta_texto": texto_meta(version, meta),
            "nd_texto": texto_nd(medicion, version) if medicion else "N s/d · D s/d",
        })
    evaluados = verdes + rojos
    pct = round(100 * verdes / evaluados) if evaluados else None
    return {
        "area": area,
        "total": len(indicadores),
        "verdes": verdes,
        "rojos": rojos,
        "grises": grises,
        "pct_meta": pct,
        "filas": filas,
    }
