"""Alta idempotente de Dirección de Telesalud (nodos, CAPS y demanda espontánea)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent
AREA_NOMBRE = "Dirección de Telesalud"

INDICADORES = [
    {
        "nombre": "Porcentaje de hospitales provinciales con nodo de Telesalud",
        "dimension": "Estructural (capacidad instalada)",
        "formula": (
            "Cantidad de nodos de Telesalud en hospitales / "
            "Cantidad total de hospitales provinciales × 100"
        ),
        "num_desc": "Hospitales provinciales con nodo de Telesalud",
        "den_desc": "Total de hospitales provinciales",
        "fuente": "Registro de Nodos de Telesalud",
        "objetivo": "Ampliar la implementación de servicios de Telesalud en la red hospitalaria provincial.",
        "nota": (
            "Planilla INDICADORES TELESALUD. El título original decía “cantidad”; "
            "la fórmula es un porcentaje."
        ),
        "frecuencia": "mensual",
        "meta_min": 50,
        "mediciones": [
            ("mensual", 2025, 12, Decimal("15"), Decimal("50"), False, "Planilla Telesalud: 15/50 hospitales (30%) en 2025."),
            (
                "mensual",
                2026,
                9,
                Decimal("22"),
                Decimal("50"),
                False,
                "Planilla Telesalud: 22/50 hospitales (44%) a septiembre 2026. Por debajo de la meta del 50%.",
            ),
        ],
    },
    {
        "nombre": "Porcentaje de CAPS de Capital con consultorio virtual",
        "dimension": "Intervenciones Comunitarias y Cobertura Territorial",
        "formula": "Cantidad de CAPS con consultorio virtual / Cantidad total de CAPS en Capital × 100",
        "num_desc": "CAPS de Capital con consultorio virtual",
        "den_desc": "Total de CAPS en Capital",
        "fuente": "Registro de Nodos de Telesalud",
        "objetivo": "Implementar consultorios virtuales en los CAPS de Capital.",
        "nota": (
            "Planilla INDICADORES TELESALUD. Meta ≥ 90%. El valor de septiembre 2026 se interpretó "
            "como 7/17 (Excel lo había guardado como fecha)."
        ),
        "frecuencia": "mensual",
        "meta_min": 90,
        "mediciones": [
            ("mensual", 2025, 12, Decimal("0"), Decimal("17"), False, "Planilla Telesalud: 0/17 CAPS (0%) en 2025."),
            (
                "mensual",
                2026,
                9,
                Decimal("7"),
                Decimal("17"),
                True,
                "Planilla Telesalud sep-2026 interpretado como 7/17 (41%). Excel lo había convertido en fecha. VP hasta que el área lo confirme.",
            ),
        ],
    },
    {
        "nombre": "Porcentaje de demanda espontánea atendida por consultorio virtual",
        "dimension": "Gestión Específica del Área",
        "formula": "Consultas de demanda espontánea virtuales / (presenciales + virtuales) × 100",
        "num_desc": "Consultas de demanda espontánea virtuales",
        "den_desc": "Total de consultas de demanda espontánea (presenciales + virtuales)",
        "fuente": "Registro de Consultas de Telesalud",
        "objetivo": "Medir qué parte de la demanda espontánea se resuelve por consultorio virtual.",
        "nota": (
            "Definido por el área como proporción sobre toda la demanda espontánea "
            "(no como razón entre dos universos). Meta ≥ 10% en 2026. "
            "El 168/3952 de la planilla se tomó como 168 virtuales y 3952 presenciales, "
            "confirmado por el área."
        ),
        "frecuencia": "trimestral",
        "meta_min": 10,
        "mediciones": [
            (
                "trimestral",
                2025,
                4,
                Decimal("168"),
                Decimal("4120"),
                False,
                "Planilla Telesalud 2025: 168 virtuales / (3952 presenciales + 168 virtuales) = 4,1%. Por debajo de la meta del 10%.",
            ),
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


def _upsert_medicion(sb, version_id, periodo, num, den, conclusion, usuario_id, es_prueba):
    valor = (num / den * Decimal("100")).quantize(Decimal("0.0001"))
    sb.table("indicadores_medicion").upsert(
        {
            "indicador_version_id": version_id,
            "periodo_id": periodo["id"],
            "fecha_corte": periodo["fecha_fin"],
            "numerador_valor": float(num),
            "denominador_valor": float(den),
            "valor_calculado": float(valor),
            "es_prueba": bool(es_prueba),
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
        {"area_id": area["id"], "nombre": "Responsable Dirección de Telesalud"},
        {
            "area_id": area["id"],
            "nombre": "Responsable Dirección de Telesalud",
            "correo": "telesalud@salud.corrientes.gob.ar",
        },
    )
    print(f"Responsable id={responsable['id']} {'alta' if alta_resp else 'ya existia'}")

    user, alta_user = _get_or_insert(
        sb,
        "cuentas_usuario",
        {"email": "telesalud@local"},
        {
            "username": "telesalud",
            "email": "telesalud@local",
            "nombre": "Referente Dirección de Telesalud",
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
                        "meta_tipo": "minimo",
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
            sb.table("indicadores_indicadorversion").update(
                {
                    "formula_calculo": data["formula"],
                    "numerador_descripcion": data["num_desc"],
                    "denominador_descripcion": data["den_desc"],
                    "nota_metodologica": data["nota"],
                }
            ).eq("id", version["id"]).execute()
            print(f"Indicador {indicador['id']} ya existia {'(alta fila)' if alta_ind else ''}")

        metas = (
            sb.table("indicadores_metaperiodo")
            .select("id")
            .eq("indicador_version_id", version["id"])
            .execute()
            .data
            or []
        )
        if not metas:
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
        else:
            print(f"  metas ya existian ({len(metas)})")

        for freq, anio, nro, num, den, es_prueba, conclusion in data["mediciones"]:
            periodo = _periodo(sb, freq, anio, nro)
            valor = _upsert_medicion(
                sb, version["id"], periodo, num, den, conclusion, admin["id"], es_prueba
            )
            marca = " VP" if es_prueba else ""
            print(f"  {periodo['label']}: {valor}%{marca}")


if __name__ == "__main__":
    main()
