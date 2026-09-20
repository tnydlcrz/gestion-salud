from .db import execute, fetch_all, fetch_one
from .logic import calcular_valor, meta_para, semaforo, texto_meta, texto_nd


def areas_visibles(user):
    if user["es_admin"]:
        return fetch_all("SELECT id, nombre FROM indicadores_areadireccion ORDER BY nombre")
    return fetch_all(
        """
        SELECT DISTINCT a.id, a.nombre
        FROM indicadores_areadireccion a
        JOIN cuentas_usuarioarea ua ON ua.area_id = a.id
        WHERE ua.usuario_id = %s AND ua.fecha_baja IS NULL
        ORDER BY a.nombre
        """,
        (user["id"],),
    )


def puede_ver_area(user, area_id):
    return any(area["id"] == area_id for area in areas_visibles(user))


def _metas_por_version(version_ids):
    if not version_ids:
        return {}
    filas = fetch_all(
        """
        SELECT indicador_version_id, meta_min, meta_max, fecha_inicio_meta, fecha_fin_meta
        FROM indicadores_metaperiodo
        WHERE indicador_version_id = ANY(%s)
        ORDER BY fecha_inicio_meta
        """,
        (version_ids,),
    )
    por = {}
    for fila in filas:
        por.setdefault(fila["indicador_version_id"], []).append(fila)
    return por


def _mediciones_por_version(version_ids):
    if not version_ids:
        return {}
    filas = fetch_all(
        """
        SELECT m.indicador_version_id, m.id, m.fecha_corte, m.numerador_valor, m.denominador_valor,
               m.valor_calculado, m.es_prueba, m.conclusion, m.estado, m.periodo_id,
               p.label, p.anio, p.fecha_inicio, p.fecha_fin
        FROM indicadores_medicion m
        JOIN indicadores_periodo p ON p.id = m.periodo_id
        WHERE m.indicador_version_id = ANY(%s) AND m.estado = 'publicado'
        ORDER BY p.fecha_inicio
        """,
        (version_ids,),
    )
    por = {}
    for fila in filas:
        por.setdefault(fila["indicador_version_id"], []).append(fila)
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
            else "N s/d · D s/d"
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
    filas = fetch_all(
        """
        SELECT i.id, i.nombre, i.area_id, i.area_direccion, i.dimension_id,
               d.nombre AS dimension_nombre,
               v.id AS version_id, v.tipo_calculo, v.unidad_resultado, v.meta_tipo,
               v.sentido_mejora, v.frecuencia, v.formula_calculo, v.fuente_datos,
               v.objetivo_operativo
        FROM indicadores_indicador i
        JOIN indicadores_dimension d ON d.id = i.dimension_id
        LEFT JOIN indicadores_indicadorversion v
          ON v.indicador_id = i.id AND v.fecha_vigencia_hasta IS NULL
        WHERE i.activo AND i.area_id = %s
        ORDER BY d.nombre, i.nombre
        """,
        (area_id,),
    )
    return _enriquecer(filas)


def indicador_detalle(indicador_id):
    fila = fetch_one(
        """
        SELECT i.id, i.nombre, i.area_id, i.area_direccion, i.dimension_id,
               a.nombre AS area_nombre, d.nombre AS dimension_nombre,
               v.id AS version_id, v.tipo_calculo, v.unidad_resultado, v.meta_tipo,
               v.sentido_mejora, v.frecuencia, v.formula_calculo, v.fuente_datos,
               v.objetivo_operativo
        FROM indicadores_indicador i
        JOIN indicadores_areadireccion a ON a.id = i.area_id
        JOIN indicadores_dimension d ON d.id = i.dimension_id
        LEFT JOIN indicadores_indicadorversion v
          ON v.indicador_id = i.id AND v.fecha_vigencia_hasta IS NULL
        WHERE i.id = %s
        """,
        (indicador_id,),
    )
    if not fila:
        return None
    return _enriquecer([fila])[0]


def resumenes_areas(user):
    areas = areas_visibles(user)
    if not areas:
        return []
    ids = [area["id"] for area in areas]
    indicadores = fetch_all(
        """
        SELECT i.id, i.nombre, i.area_id, i.area_direccion, i.dimension_id,
               d.nombre AS dimension_nombre,
               v.id AS version_id, v.tipo_calculo, v.unidad_resultado, v.meta_tipo,
               v.sentido_mejora, v.frecuencia, v.formula_calculo, v.fuente_datos,
               v.objetivo_operativo
        FROM indicadores_indicador i
        JOIN indicadores_dimension d ON d.id = i.dimension_id
        LEFT JOIN indicadores_indicadorversion v
          ON v.indicador_id = i.id AND v.fecha_vigencia_hasta IS NULL
        WHERE i.activo AND i.area_id = ANY(%s)
        """,
        (ids,),
    )
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
    return fetch_all(
        """
        SELECT id, label, fecha_fin
        FROM indicadores_periodo
        WHERE frecuencia = %s
        ORDER BY fecha_inicio DESC
        """,
        (frecuencia,),
    )


def guardar_medicion(user, indicador, periodo_id, numerador, denominador, conclusion, es_prueba, estado):
    version_id = indicador["version_id"]
    periodo = fetch_one("SELECT id, fecha_fin FROM indicadores_periodo WHERE id = %s", (periodo_id,))
    if not version_id or not periodo:
        raise ValueError("Faltan versión o período.")
    valor = calcular_valor(
        indicador["tipo_calculo"],
        indicador["unidad_resultado"],
        numerador,
        denominador,
    )
    execute(
        """
        INSERT INTO indicadores_medicion (
            indicador_version_id, periodo_id, fecha_corte, numerador_valor, denominador_valor,
            valor_calculado, es_prueba, conclusion, estado, usuario_carga_id, fecha_carga
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (indicador_version_id, periodo_id)
        DO UPDATE SET
            fecha_corte = EXCLUDED.fecha_corte,
            numerador_valor = EXCLUDED.numerador_valor,
            denominador_valor = EXCLUDED.denominador_valor,
            valor_calculado = EXCLUDED.valor_calculado,
            es_prueba = EXCLUDED.es_prueba,
            conclusion = EXCLUDED.conclusion,
            estado = EXCLUDED.estado,
            usuario_carga_id = EXCLUDED.usuario_carga_id,
            fecha_carga = NOW()
        """,
        (
            version_id,
            periodo["id"],
            periodo["fecha_fin"],
            numerador,
            denominador,
            valor,
            es_prueba,
            conclusion or "",
            estado,
            user["id"],
        ),
    )
