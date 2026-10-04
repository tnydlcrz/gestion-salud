"""Alta idempotente del indicador SUMAR+ de antigüedad y mediciones de agosto 2026."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent

NOTA_AMARILLO = (
    "Planilla SUMAR+ agosto 2026. El semáforo de tres colores "
    "(amarillo 61–90 días) queda pendiente de modelar con el resto de áreas."
)


def _json(valor):
    if valor is None:
        return None
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    return valor


def _calcular(tipo_calculo, unidad, numerador, denominador):
    if numerador is None:
        return None
    if tipo_calculo == "valor_directo":
        return Decimal(str(numerador))
    if denominador in (None, 0, Decimal("0")):
        return None
    razon = Decimal(str(numerador)) / Decimal(str(denominador))
    if (unidad or "").strip() == "%":
        return (razon * Decimal("100")).quantize(Decimal("0.0001"))
    return razon.quantize(Decimal("0.0001"))


def _supabase():
    url = ""
    key = ""
    secrets = ROOT / ".streamlit" / "secrets.toml"
    if secrets.exists():
        for linea in secrets.read_text(encoding="utf-8").splitlines():
            if linea.startswith("SUPABASE_URL"):
                url = linea.split("=", 1)[1].strip().strip('"')
            if linea.startswith("SUPABASE_SERVICE_ROLE_KEY"):
                key = linea.split("=", 1)[1].strip().strip('"')
    if not url or not key:
        raise SystemExit("Falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en .streamlit/secrets.toml")
    return create_client(url, key)


def _uno(sb, tabla, **filtros):
    consulta = sb.table(tabla).select("*")
    for clave, valor in filtros.items():
        consulta = consulta.eq(clave, valor)
    filas = consulta.limit(1).execute().data or []
    return filas[0] if filas else None


def _periodo(sb, anio, frecuencia, nro):
    fila = _uno(sb, "indicadores_periodo", anio=anio, frecuencia=frecuencia, nro_periodo=nro)
    if not fila:
        raise SystemExit(f"No está el período {frecuencia} {nro}/{anio}.")
    return fila


def _upsert_medicion(sb, version_id, periodo, tipo_calculo, unidad, num, den, conclusion, usuario_id, es_prueba=False):
    valor = _calcular(tipo_calculo, unidad, num, den)
    payload = {
        "indicador_version_id": version_id,
        "periodo_id": periodo["id"],
        "fecha_corte": periodo["fecha_fin"],
        "numerador_valor": _json(num),
        "denominador_valor": _json(den),
        "valor_calculado": _json(valor),
        "es_prueba": bool(es_prueba),
        "conclusion": conclusion,
        "estado": "publicado",
        "usuario_carga_id": usuario_id,
        "fecha_carga": datetime.now(timezone.utc).isoformat(),
    }
    sb.table("indicadores_medicion").upsert(
        payload, on_conflict="indicador_version_id,periodo_id"
    ).execute()
    return valor


def main():
    sb = _supabase()
    areas = sb.table("indicadores_areadireccion").select("*").execute().data or []
    area = next((item for item in areas if item["nombre"].casefold() == "sumar+"), None)
    dimension = _uno(
        sb,
        "indicadores_dimension",
        nombre="Producción/Gestión Administrativa y/o Presupuestaria",
    )
    responsable = None
    if area:
        responsables = (
            sb.table("indicadores_responsable").select("*").eq("area_id", area["id"]).execute().data or []
        )
        responsable = next(iter(responsables), None)
    admin = _uno(sb, "cuentas_usuario", email="admin@local")
    if not all([area, dimension, responsable, admin]):
        raise SystemExit("Faltan área, dimensión, responsable o admin de SUMAR+.")

    ago = _periodo(sb, 2026, "mensual", 8)
    t3 = _periodo(sb, 2026, "trimestral", 3)

    indicador = _uno(
        sb,
        "indicadores_indicador",
        nombre="Antigüedad de las Prestaciones Recibidas en el Mes",
        area_id=area["id"],
    )
    if not indicador:
        creado = (
            sb.table("indicadores_indicador")
            .insert(
                {
                    "nombre": "Antigüedad de las Prestaciones Recibidas en el Mes",
                    "area_id": area["id"],
                    "area_direccion": "Auditoría · Facturación",
                    "dimension_id": dimension["id"],
                    "responsable_id": responsable["id"],
                    "activo": True,
                    "creado_por_id": admin["id"],
                    "actualizado_por_id": admin["id"],
                }
            )
            .execute()
            .data
        )
        indicador = creado[0]
        print(f"Alta indicador id={indicador['id']}")
    else:
        print(f"Indicador ya existia id={indicador['id']}")

    version = _uno(sb, "indicadores_indicadorversion", indicador_id=indicador["id"])
    if not version:
        creado = (
            sb.table("indicadores_indicadorversion")
            .insert(
                {
                    "indicador_id": indicador["id"],
                    "version_num": 1,
                    "fecha_vigencia_desde": "2025-01-01",
                    "formula_calculo": (
                        "Promedio de fecha de recepción de las facturas recibidas "
                        "en el mes − promedio de fecha de las prestaciones"
                    ),
                    "tipo_calculo": "valor_directo",
                    "numerador_descripcion": "Días promedio entre prestación y recepción de factura",
                    "numerador_unidad": "días",
                    "denominador_descripcion": "",
                    "denominador_unidad": "",
                    "unidad_resultado": "días",
                    "meta_tipo": "maximo",
                    "sentido_mejora": "descendente",
                    "fuente_datos": "Auditoría de facturación",
                    "frecuencia": "mensual",
                    "objetivo_operativo": "",
                    "nota_metodologica": NOTA_AMARILLO,
                }
            )
            .execute()
            .data
        )
        version = creado[0]
        sb.table("indicadores_metaperiodo").insert(
            {
                "indicador_version_id": version["id"],
                "meta_min": None,
                "meta_max": 60,
                "fecha_inicio_meta": "2025-01-01",
                "fecha_fin_meta": "2026-12-31",
            }
        ).execute()
        print(f"Alta version id={version['id']} y meta max 60 dias")
    else:
        print(f"Version ya existia id={version['id']}")

    cobertura = _uno(sb, "indicadores_indicador", nombre="Cobertura efectiva Básica", area_id=area["id"])
    if cobertura:
        ver_ceb = _uno(sb, "indicadores_indicadorversion", indicador_id=cobertura["id"])
        if ver_ceb:
            metas = (
                sb.table("indicadores_metaperiodo")
                .select("id,meta_min")
                .eq("indicador_version_id", ver_ceb["id"])
                .execute()
                .data
                or []
            )
            for meta in metas:
                if float(meta.get("meta_min") or 0) != 35:
                    sb.table("indicadores_metaperiodo").update({"meta_min": 35}).eq("id", meta["id"]).execute()
                    print(f"Meta cobertura id={meta['id']}: 39 -> 35")
            sb.table("indicadores_indicadorversion").update(
                {
                    "nota_metodologica": (
                        "Meta ≥ 35% según planilla SUMAR+ agosto 2026. "
                        "Valores mensuales 2026 previos a agosto son de prueba."
                    )
                }
            ).eq("id", ver_ceb["id"]).execute()

    mediciones = [
        (
            "Antigüedad de las Prestaciones Recibidas en el Mes",
            version,
            ago,
            Decimal("71"),
            None,
            "Planilla SUMAR+ agosto 2026 (9/8/2026 vs 30/5/2026 = 71 días).",
        ),
    ]
    existentes = {
        "Cobertura efectiva Básica": (
            ago,
            Decimal("209006"),
            Decimal("576282"),
            "Planilla SUMAR+ agosto 2026 (209.006 / 576.282 = 36,27%).",
        ),
        "Porcentaje de efectores facturantes": (
            t3,
            Decimal("205"),
            Decimal("270"),
            "Planilla SUMAR+ agosto 2026 (205 / 270 = 75,93%).",
        ),
        "Porcentaje de efectores con convenio": (
            ago,
            Decimal("270"),
            Decimal("387"),
            "Planilla SUMAR+ agosto 2026 (270 / 387 = 69,77%).",
        ),
        "Plazo de Pago a los efectores": (
            ago,
            Decimal("38"),
            None,
            "Planilla SUMAR+ agosto 2026 (4/7/2026 vs 11/8/2026 = 38 días).",
        ),
    }
    for nombre, (periodo, num, den, conclusion) in existentes.items():
        ind = _uno(sb, "indicadores_indicador", nombre=nombre, area_id=area["id"])
        if not ind:
            raise SystemExit(f"No está el indicador {nombre}.")
        ver = _uno(sb, "indicadores_indicadorversion", indicador_id=ind["id"])
        if not ver:
            raise SystemExit(f"No hay versión vigente de {nombre}.")
        mediciones.append((nombre, ver, periodo, num, den, conclusion))

    for nombre, ver, periodo, num, den, conclusion in mediciones:
        valor = _upsert_medicion(
            sb,
            ver["id"],
            periodo,
            ver["tipo_calculo"],
            ver["unidad_resultado"],
            num,
            den,
            conclusion,
            admin["id"],
        )
        print(f"{nombre}: {periodo['label']} -> {valor} {ver['unidad_resultado']}")


if __name__ == "__main__":
    main()
