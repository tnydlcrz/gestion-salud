"""Alta idempotente del área Dirección de Inmunizaciones (propuesta 2026)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent
AREA_NOMBRE = "Dirección de Inmunizaciones"

INDICADORES = [
    {
        "nombre": "Cumplimiento de las metas de cobertura de vacunación en la población objetivo",
        "dimension": "Gestión Específica del Área",
        "formula": (
            "N.º de personas vacunadas según vacuna y población objetivo ÷ "
            "población objetivo establecida × 100"
        ),
        "num_desc": "Personas vacunadas según vacuna y población objetivo",
        "den_desc": "Población objetivo establecida",
        "meta_tipo": "seguimiento",
        "frecuencia": "trimestral",
        "fuente": "NOMIVAC/SISA, poblaciones objetivo oficiales e informes de cobertura",
        "objetivo": "Evaluar el alcance de las estrategias de inmunización respecto de la población objetivo de cada vacuna.",
        "nota": (
            "Propuesta 2026. La planilla indica meta según cada vacuna; queda en seguimiento "
            "hasta que el área fije un umbral provincial único para el semáforo."
        ),
        "meta_min": None,
        "mediciones": [
            ("trimestral", 2026, 1, Decimal("82"), Decimal("100"), "Valor de prueba 2026. En seguimiento (meta por vacuna)."),
            ("trimestral", 2026, 2, Decimal("88"), Decimal("100"), "Valor de prueba 2026. En seguimiento (meta por vacuna)."),
        ],
    },
    {
        "nombre": "Disponibilidad y abastecimiento de vacunas e insumos en la Red Provincial de Vacunación",
        "dimension": "Gestión Específica del Área",
        "formula": (
            "N.º de vacunatorios abastecidos según requerimiento/programación ÷ "
            "total de vacunatorios con requerimiento/programación × 100"
        ),
        "num_desc": "Vacunatorios abastecidos según requerimiento/programación",
        "den_desc": "Vacunatorios con requerimiento/programación",
        "meta_tipo": "minimo",
        "frecuencia": "mensual",
        "fuente": "Stock provincial, solicitudes, remitos y planillas de distribución",
        "objetivo": "Garantizar la disponibilidad de vacunas e insumos para la continuidad de la vacunación en Capital e interior.",
        "nota": "Propuesta 2026. Valores de prueba.",
        "meta_min": 95,
        "mediciones": [
            ("mensual", 2026, 1, Decimal("91"), Decimal("100"), "Valor de prueba 2026. Por debajo del 95%."),
            ("mensual", 2026, 2, Decimal("93"), Decimal("100"), "Valor de prueba 2026."),
            ("mensual", 2026, 3, Decimal("96"), Decimal("100"), "Valor de prueba 2026. Alcanza la meta."),
            ("mensual", 2026, 4, Decimal("94"), Decimal("100"), "Valor de prueba 2026."),
            ("mensual", 2026, 5, Decimal("97"), Decimal("100"), "Valor de prueba 2026."),
            ("mensual", 2026, 6, Decimal("98"), Decimal("100"), "Valor de prueba 2026."),
        ],
    },
    {
        "nombre": "Cumplimiento de las actividades de capacitación y actualización de los equipos de vacunación",
        "dimension": "Capacitaciones",
        "formula": "N.º de actividades de capacitación realizadas ÷ N.º de actividades programadas × 100",
        "num_desc": "Actividades de capacitación realizadas",
        "den_desc": "Actividades de capacitación programadas",
        "meta_tipo": "minimo",
        "frecuencia": "trimestral",
        "fuente": "Cronograma, registros de asistencia, informes y documentación de capacitación",
        "objetivo": "Medir el cumplimiento de las instancias de formación destinadas a los equipos de vacunación.",
        "nota": "Propuesta 2026. Valores de prueba.",
        "meta_min": 90,
        "mediciones": [
            ("trimestral", 2026, 1, Decimal("80"), Decimal("100"), "Valor de prueba 2026. Por debajo del 90%."),
            ("trimestral", 2026, 2, Decimal("94"), Decimal("100"), "Valor de prueba 2026. Superó la meta."),
        ],
    },
    {
        "nombre": "Oportunidad y cumplimiento del registro y monitoreo de información de inmunizaciones",
        "dimension": "Producción/Gestión Administrativa y/o Presupuestaria",
        "formula": (
            "N.º de vacunatorios que cumplen con los registros/reportes requeridos en el período ÷ "
            "total de vacunatorios que deben informar × 100"
        ),
        "num_desc": "Vacunatorios que cumplen registros/reportes requeridos",
        "den_desc": "Vacunatorios que deben informar",
        "meta_tipo": "minimo",
        "frecuencia": "mensual",
        "fuente": "NOMIVAC/SISA, reportes de stock, planillas de seguimiento e informes",
        "objetivo": "Evaluar el cumplimiento y la oportunidad de la información de inmunizaciones remitida por los vacunatorios.",
        "nota": "Propuesta 2026. Valores de prueba.",
        "meta_min": 90,
        "mediciones": [
            ("mensual", 2026, 1, Decimal("86"), Decimal("100"), "Valor de prueba 2026. Por debajo del 90%."),
            ("mensual", 2026, 2, Decimal("88"), Decimal("100"), "Valor de prueba 2026."),
            ("mensual", 2026, 3, Decimal("91"), Decimal("100"), "Valor de prueba 2026. Alcanza la meta."),
            ("mensual", 2026, 4, Decimal("89"), Decimal("100"), "Valor de prueba 2026."),
            ("mensual", 2026, 5, Decimal("93"), Decimal("100"), "Valor de prueba 2026."),
            ("mensual", 2026, 6, Decimal("95"), Decimal("100"), "Valor de prueba 2026."),
        ],
    },
    {
        "nombre": "Cumplimiento de las estrategias de vacunación programadas en el territorio provincial",
        "dimension": "Intervenciones Comunitarias y Cobertura Territorial",
        "formula": "N.º de acciones territoriales realizadas ÷ N.º de acciones territoriales programadas × 100",
        "num_desc": "Acciones territoriales realizadas",
        "den_desc": "Acciones territoriales programadas",
        "meta_tipo": "minimo",
        "frecuencia": "mensual",
        "fuente": "Cronogramas, informes de operativos, registros de vacunación y planillas de actividades",
        "objetivo": "Evaluar el desarrollo de las estrategias de vacunación en el territorio provincial (puntos fijos, escuelas, extramuros y operativos).",
        "nota": "Propuesta 2026. Valores de prueba.",
        "meta_min": 90,
        "mediciones": [
            ("mensual", 2026, 1, Decimal("84"), Decimal("100"), "Valor de prueba 2026. Por debajo del 90%."),
            ("mensual", 2026, 2, Decimal("90"), Decimal("100"), "Valor de prueba 2026. Alcanza la meta."),
            ("mensual", 2026, 3, Decimal("92"), Decimal("100"), "Valor de prueba 2026."),
            ("mensual", 2026, 4, Decimal("87"), Decimal("100"), "Valor de prueba 2026."),
            ("mensual", 2026, 5, Decimal("94"), Decimal("100"), "Valor de prueba 2026."),
            ("mensual", 2026, 6, Decimal("91"), Decimal("100"), "Valor de prueba 2026."),
        ],
    },
]


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


def _get_or_insert(sb, tabla, match, payload):
    existente = _uno(sb, tabla, **match)
    if existente:
        return existente, False
    creado = sb.table(tabla).insert(payload).execute().data
    return creado[0], True


def _periodo(sb, frecuencia, anio, nro):
    fila = _uno(sb, "indicadores_periodo", anio=anio, frecuencia=frecuencia, nro_periodo=nro)
    if not fila:
        raise SystemExit(f"No esta el periodo {frecuencia} {nro}/{anio}.")
    return fila


def _upsert_medicion(sb, version_id, periodo, num, den, conclusion, usuario_id):
    valor = (num / den * Decimal("100")).quantize(Decimal("0.0001"))
    sb.table("indicadores_medicion").upsert(
        {
            "indicador_version_id": version_id,
            "periodo_id": periodo["id"],
            "fecha_corte": periodo["fecha_fin"],
            "numerador_valor": float(num),
            "denominador_valor": float(den),
            "valor_calculado": float(valor),
            "es_prueba": True,
            "conclusion": conclusion,
            "estado": "publicado",
            "usuario_carga_id": usuario_id,
            "fecha_carga": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="indicador_version_id,periodo_id",
    ).execute()
    return valor


def main():
    sb = _supabase()
    admin = _uno(sb, "cuentas_usuario", email="admin@local")
    dims = {
        item["nombre"]: item
        for item in (sb.table("indicadores_dimension").select("id,nombre").execute().data or [])
    }
    if not admin:
        raise SystemExit("Falta admin@local.")

    area, alta_area = _get_or_insert(
        sb,
        "indicadores_areadireccion",
        {"nombre": AREA_NOMBRE},
        {"nombre": AREA_NOMBRE},
    )
    print(f"Area id={area['id']} {'alta' if alta_area else 'ya existia'}")

    responsable, alta_resp = _get_or_insert(
        sb,
        "indicadores_responsable",
        {"area_id": area["id"], "nombre": "Responsable Dirección de Inmunizaciones"},
        {
            "area_id": area["id"],
            "nombre": "Responsable Dirección de Inmunizaciones",
            "correo": "inmunizaciones@salud.corrientes.gob.ar",
        },
    )
    print(f"Responsable id={responsable['id']} {'alta' if alta_resp else 'ya existia'}")

    user, alta_user = _get_or_insert(
        sb,
        "cuentas_usuario",
        {"email": "inmuniz@local"},
        {
            "username": "inmuniz",
            "email": "inmuniz@local",
            "nombre": "Referente Dirección de Inmunizaciones",
            "password": admin["password"],
            "is_active": True,
            "es_admin_global": False,
            "is_superuser": False,
            "is_staff": False,
        },
    )
    print(f"Usuario id={user['id']} {'alta' if alta_user else 'ya existia'}")

    vinculo = (
        sb.table("cuentas_usuarioarea")
        .select("id")
        .eq("usuario_id", user["id"])
        .eq("area_id", area["id"])
        .is_("fecha_baja", "null")
        .limit(1)
        .execute()
        .data
        or []
    )
    if not vinculo:
        sb.table("cuentas_usuarioarea").insert(
            {
                "usuario_id": user["id"],
                "area_id": area["id"],
                "rol": "area",
                "otorgado_por_id": admin["id"],
            }
        ).execute()
        print("Alta vinculo usuario-area")
    else:
        print("Vinculo usuario-area ya existia")

    for data in INDICADORES:
        dimension = dims.get(data["dimension"])
        if not dimension:
            raise SystemExit(f"Falta dimension {data['dimension']}.")
        indicador, alta_ind = _get_or_insert(
            sb,
            "indicadores_indicador",
            {"nombre": data["nombre"], "area_id": area["id"]},
            {
                "nombre": data["nombre"],
                "area_id": area["id"],
                "area_direccion": AREA_NOMBRE,
                "dimension_id": dimension["id"],
                "responsable_id": responsable["id"],
                "activo": True,
                "creado_por_id": admin["id"],
                "actualizado_por_id": admin["id"],
            },
        )
        version = _uno(sb, "indicadores_indicadorversion", indicador_id=indicador["id"])
        if not version:
            version = (
                sb.table("indicadores_indicadorversion")
                .insert(
                    {
                        "indicador_id": indicador["id"],
                        "version_num": 1,
                        "fecha_vigencia_desde": "2025-01-01",
                        "formula_calculo": data["formula"],
                        "tipo_calculo": "razon",
                        "numerador_descripcion": data["num_desc"],
                        "numerador_unidad": "",
                        "denominador_descripcion": data["den_desc"],
                        "denominador_unidad": "",
                        "unidad_resultado": "%",
                        "meta_tipo": data["meta_tipo"],
                        "sentido_mejora": "ascendente",
                        "fuente_datos": data["fuente"],
                        "frecuencia": data["frecuencia"],
                        "objetivo_operativo": data["objetivo"],
                        "nota_metodologica": data["nota"],
                    }
                )
                .execute()
                .data
            )[0]
            print(f"Alta indicador {indicador['id']} {data['nombre']}")
        else:
            print(f"Indicador {indicador['id']} ya existia {'(alta fila)' if alta_ind else ''}")

        metas = (
            sb.table("indicadores_metaperiodo")
            .select("id")
            .eq("indicador_version_id", version["id"])
            .execute()
            .data
            or []
        )
        if not metas and data["meta_tipo"] != "seguimiento":
            sb.table("indicadores_metaperiodo").insert(
                {
                    "indicador_version_id": version["id"],
                    "meta_min": data["meta_min"],
                    "meta_max": None,
                    "fecha_inicio_meta": "2025-01-01",
                    "fecha_fin_meta": "2026-12-31",
                }
            ).execute()
            print(f"  meta >= {data['meta_min']}")
        elif metas:
            print(f"  metas ya existian ({len(metas)})")
        else:
            print("  seguimiento (sin umbral de semaforo)")

        for freq, anio, nro, num, den, conclusion in data["mediciones"]:
            periodo = _periodo(sb, freq, anio, nro)
            valor = _upsert_medicion(sb, version["id"], periodo, num, den, conclusion, admin["id"])
            print(f"  {periodo['label']}: {valor}% (VP)")


if __name__ == "__main__":
    main()
