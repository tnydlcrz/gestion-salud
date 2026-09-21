from datetime import date, datetime, timezone
from decimal import Decimal

from .logic import calcular_valor, meta_para, semaforo, texto_meta, texto_nd
from .supabase_client import get_client


def _tabla(nombre):
    return get_client().table(nombre)


def _fecha(valor):
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor)[:10])


def _num(valor):
    if valor is None or valor == "":
        return None
    if isinstance(valor, Decimal):
        return valor
    return Decimal(str(valor))


def _json(valor):
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    return valor


def areas_visibles(user):
    from .data_cache import areas_visibles_cached

    return areas_visibles_cached(int(user["id"]), bool(user["es_admin"]))


def _areas_visibles_impl(user_id, es_admin):
    if es_admin:
        data = _tabla("indicadores_areadireccion").select("id,nombre").order("nombre").execute().data or []
        return data
    filas = (
        _tabla("cuentas_usuarioarea")
        .select("area:indicadores_areadireccion(id,nombre)")
        .eq("usuario_id", user_id)
        .is_("fecha_baja", "null")
        .execute()
        .data
        or []
    )
    vistos = {}
    for fila in filas:
        area = fila.get("area")
        if area and area["id"] not in vistos:
            vistos[area["id"]] = area
    return sorted(vistos.values(), key=lambda item: item["nombre"])


def puede_ver_area(user, area_id):
    return any(area["id"] == area_id for area in areas_visibles(user))


def _metas_por_version(version_ids):
    if not version_ids:
        return {}
    filas = (
        _tabla("indicadores_metaperiodo")
        .select("indicador_version_id,meta_min,meta_max,fecha_inicio_meta,fecha_fin_meta")
        .in_("indicador_version_id", version_ids)
        .order("fecha_inicio_meta")
        .execute()
        .data
        or []
    )
    por = {}
    for fila in filas:
        fila["fecha_inicio_meta"] = _fecha(fila.get("fecha_inicio_meta"))
        fila["fecha_fin_meta"] = _fecha(fila.get("fecha_fin_meta"))
        fila["meta_min"] = _num(fila.get("meta_min"))
        fila["meta_max"] = _num(fila.get("meta_max"))
        por.setdefault(fila["indicador_version_id"], []).append(fila)
    return por


def _mediciones_por_version(version_ids):
    if not version_ids:
        return {}
    filas = (
        _tabla("indicadores_medicion")
        .select(
            "indicador_version_id,id,fecha_corte,numerador_valor,denominador_valor,"
            "valor_calculado,es_prueba,conclusion,estado,periodo_id,"
            "periodo:indicadores_periodo(label,anio,fecha_inicio,fecha_fin)"
        )
        .in_("indicador_version_id", version_ids)
        .eq("estado", "publicado")
        .execute()
        .data
        or []
    )
    por = {}
    for fila in filas:
        periodo = fila.pop("periodo", None) or {}
        fila["label"] = periodo.get("label")
        fila["anio"] = periodo.get("anio")
        fila["fecha_inicio"] = _fecha(periodo.get("fecha_inicio"))
        fila["fecha_fin"] = _fecha(periodo.get("fecha_fin"))
        fila["fecha_corte"] = _fecha(fila.get("fecha_corte"))
        fila["numerador_valor"] = _num(fila.get("numerador_valor"))
        fila["denominador_valor"] = _num(fila.get("denominador_valor"))
        fila["valor_calculado"] = _num(fila.get("valor_calculado"))
        por.setdefault(fila["indicador_version_id"], []).append(fila)
    for lista in por.values():
        lista.sort(key=lambda item: item.get("fecha_inicio") or date.min)
    return por


def _enriquecer(indicadores):
    version_ids = [item["version_id"] for item in indicadores if item.get("version_id")]
    metas = _metas_por_version(version_ids)
    mediciones = _mediciones_por_version(version_ids)
    for item in indicadores:
        vid = item.get("version_id")
        item["metas"] = metas.get(vid, [])
        item["mediciones"] = mediciones.get(vid, [])
        ultima = item["mediciones"][-1] if item["mediciones"] else None
        item["ultima"] = ultima
        meta = meta_para(item["metas"], ultima["fecha_corte"]) if ultima else (
            item["metas"][-1] if item["metas"] else None
        )
        item["meta"] = meta
        item["semaforo"] = (
            semaforo(
                item.get("meta_tipo"),
                ultima["valor_calculado"] if ultima else None,
                meta["meta_min"] if meta else None,
                meta["meta_max"] if meta else None,
            )
            if ultima
            else "gris"
        )
        item["meta_texto"] = texto_meta(
            item.get("meta_tipo"),
            item.get("unidad_resultado"),
            meta["meta_min"] if meta else None,
            meta["meta_max"] if meta else None,
        )
        item["nd_texto"] = (
            texto_nd(
                ultima["numerador_valor"],
                ultima["denominador_valor"],
                item.get("tipo_calculo") == "razon",
                ultima["es_prueba"],
            )
            if ultima
            else "Numerador s/d · Denominador s/d"
        )
        serie = []
        for med in item["mediciones"]:
            meta_p = meta_para(item["metas"], med["fecha_corte"])
            color = semaforo(
                item.get("meta_tipo"),
                med["valor_calculado"],
                meta_p["meta_min"] if meta_p else None,
                meta_p["meta_max"] if meta_p else None,
            )
            serie.append(
                {
                    "label": med["label"],
                    "valor": float(med["valor_calculado"]) if med["valor_calculado"] is not None else None,
                    "color": {"verde": "#0f766e", "rojo": "#b91c1c", "gris": "#94a3b8"}[color],
                }
            )
        item["serie"] = serie
    return indicadores


def indicadores_de_area(area_id):
    from .data_cache import indicadores_de_area_cached

    return indicadores_de_area_cached(int(area_id))


def _indicadores_de_area_impl(area_id):
    filas = (
        _tabla("v_indicadores_base")
        .select("*")
        .eq("activo", True)
        .eq("area_id", area_id)
        .order("dimension_nombre")
        .order("nombre")
        .execute()
        .data
        or []
    )
    return _enriquecer(filas)


def indicador_detalle(indicador_id):
    from .data_cache import indicador_detalle_cached

    return indicador_detalle_cached(int(indicador_id))


def _indicador_detalle_impl(indicador_id):
    filas = (
        _tabla("v_indicadores_base")
        .select("*")
        .eq("id", indicador_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not filas:
        return None
    return _enriquecer(filas)[0]


def resumenes_areas(user):
    from .data_cache import resumenes_areas_cached

    return resumenes_areas_cached(int(user["id"]), bool(user["es_admin"]))


def _resumenes_areas_impl(user_id, es_admin):
    areas = _areas_visibles_impl(user_id, es_admin)
    if not areas:
        return []
    ids = [area["id"] for area in areas]
    consulta = _tabla("v_indicadores_base").select("*").eq("activo", True)
    if len(ids) == 1:
        consulta = consulta.eq("area_id", ids[0])
    else:
        consulta = consulta.in_("area_id", ids)
    indicadores = consulta.execute().data or []
    _enriquecer(indicadores)
    por_area = {}
    for item in indicadores:
        por_area.setdefault(item["area_id"], []).append(item)
    resumenes = []
    for area in areas:
        filas = por_area.get(area["id"], [])
        verdes = sum(1 for item in filas if item["semaforo"] == "verde")
        rojos = sum(1 for item in filas if item["semaforo"] == "rojo")
        grises = sum(1 for item in filas if item["semaforo"] == "gris")
        evaluados = verdes + rojos
        resumenes.append(
            {
                "area": area,
                "total": len(filas),
                "verdes": verdes,
                "rojos": rojos,
                "grises": grises,
                "pct_meta": round(100 * verdes / evaluados) if evaluados else None,
            }
        )
    return resumenes


def periodos_de(frecuencia):
    from .data_cache import periodos_de_cached

    return periodos_de_cached(frecuencia)


def _periodos_de_impl(frecuencia):
    return (
        _tabla("indicadores_periodo")
        .select("id,label,fecha_fin")
        .eq("frecuencia", frecuencia)
        .order("fecha_inicio", desc=True)
        .execute()
        .data
        or []
    )


def guardar_medicion(user, indicador, periodo_id, numerador, denominador, conclusion, es_prueba, estado):
    version_id = indicador["version_id"]
    periodos = (
        _tabla("indicadores_periodo")
        .select("id,fecha_fin")
        .eq("id", periodo_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    periodo = periodos[0] if periodos else None
    if not version_id or not periodo:
        raise ValueError("Faltan versión o período.")
    valor = calcular_valor(
        indicador["tipo_calculo"],
        indicador["unidad_resultado"],
        numerador,
        denominador,
    )
    payload = {
        "indicador_version_id": version_id,
        "periodo_id": periodo["id"],
        "fecha_corte": str(_fecha(periodo["fecha_fin"]) or periodo["fecha_fin"]),
        "numerador_valor": _json(numerador),
        "denominador_valor": _json(denominador),
        "valor_calculado": _json(valor),
        "es_prueba": bool(es_prueba),
        "conclusion": conclusion or "",
        "estado": estado,
        "usuario_carga_id": user["id"],
        "fecha_carga": datetime.now(timezone.utc).isoformat(),
    }
    (
        _tabla("indicadores_medicion")
        .upsert(payload, on_conflict="indicador_version_id,periodo_id")
        .execute()
    )
    from .data_cache import invalidate_data_cache

    invalidate_data_cache()
