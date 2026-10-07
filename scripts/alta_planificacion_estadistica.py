"""Alta idempotente del área Planificación y Estadística (primera tanda)."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from supabase import create_client

ROOT = Path(__file__).resolve().parent.parent
AREA_NOMBRE = "Dirección General de Planificación y Estadística"

INDICADORES = [
    {
        "nombre": "Porcentaje de informes validados sin inconsistencias",
        "formula": "Informes validados sin inconsistencias / Total de informes elaborados × 100",
        "num_desc": "Informes validados sin inconsistencias",
        "den_desc": "Total de informes elaborados",
        "objetivo": "Asegurar la calidad de los informes estadísticos antes de su difusión o envío.",
        "nota": (
            "Primera tanda: definición y metas tomadas de la tabla de resultado (31/08/2026). "
            "Año 1 = 2026. Frecuencia anual inferida de las metas anuales. "
            "Pendiente confirmar con el área si coincide con “porcentaje de registros validados” de la tabla de proceso."
        ),
        "fuente": "Control de calidad de informes del área (fuente a precisar)",
        "metas": [
            ("2026-01-01", "2026-12-31", 95),
            ("2027-01-01", "2027-12-31", 97),
            ("2028-01-01", "2028-12-31", 98),
        ],
        "mediciones": [
            (2026, Decimal("91"), Decimal("100"), "Valor de prueba. Por debajo de la meta del 95%."),
            (2027, Decimal("98"), Decimal("100"), "Valor de prueba. Superó la meta del 97%."),
            (2028, Decimal("99"), Decimal("100"), "Valor de prueba. Superó la meta del 98%."),
        ],
    },
    {
        "nombre": "Porcentaje de certificados digitales emitidos",
        "formula": "Certificados digitales emitidos / Total de certificados emitidos × 100",
        "num_desc": "Certificados digitales emitidos",
        "den_desc": "Total de certificados emitidos",
        "objetivo": "Incrementar la emisión digital de certificados respecto del total emitido.",
        "nota": (
            "Primera tanda: el más directo de la tabla de resultado (31/08/2026). "
            "Metas 50 / 80 / 100 % para 2026-2028. Frecuencia anual inferida de las metas anuales."
        ),
        "fuente": "Piloto hospitalario / Registro Civil (fuente a precisar)",
        "metas": [
            ("2026-01-01", "2026-12-31", 50),
            ("2027-01-01", "2027-12-31", 80),
            ("2028-01-01", "2028-12-31", 100),
        ],
        "mediciones": [
            (2026, Decimal("42"), Decimal("100"), "Valor de prueba. Por debajo de la meta del 50%."),
            (2027, Decimal("84"), Decimal("100"), "Valor de prueba. Superó la meta del 80%."),
            (2028, Decimal("91"), Decimal("100"), "Valor de prueba. Por debajo de la meta del 100%."),
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


def _periodo_anual(sb, anio):
    fila = _uno(sb, "indicadores_periodo", anio=anio, frecuencia="anual", nro_periodo=1)
    if fila:
        return fila
    creado = (
        sb.table("indicadores_periodo")
        .insert(
            {
                "anio": anio,
                "frecuencia": "anual",
                "nro_periodo": 1,
                "fecha_inicio": f"{anio}-01-01",
                "fecha_fin": f"{anio}-12-31",
                "label": f"Año {anio}",
            }
        )
        .execute()
        .data
    )
    return creado[0]


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


def _get_or_insert(sb, tabla, match, payload):
    existente = _uno(sb, tabla, **match)
    if existente:
        return existente, False
    creado = sb.table(tabla).insert(payload).execute().data
    return creado[0], True


def main():
    sb = _supabase()
    admin = _uno(sb, "cuentas_usuario", email="admin@local")
    dimension = _uno(sb, "indicadores_dimension", nombre="Resultados")
    if not admin or not dimension:
        raise SystemExit("Faltan admin@local o la dimension Resultados.")

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
        {"area_id": area["id"], "nombre": "Responsable Planificación y Estadística"},
        {
            "area_id": area["id"],
            "nombre": "Responsable Planificación y Estadística",
            "correo": "planificacion@salud.corrientes.gob.ar",
        },
    )
    print(f"Responsable id={responsable['id']} {'alta' if alta_resp else 'ya existia'}")

    user, alta_user = _get_or_insert(
        sb,
        "cuentas_usuario",
        {"email": "planif@local"},
        {
            "username": "planif",
            "email": "planif@local",
            "nombre": "Referente Planificación y Estadística",
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
        indicador, alta_ind = _get_or_insert(
            sb,
            "indicadores_indicador",
            {"nombre": data["nombre"], "area_id": area["id"]},
            {
                "nombre": data["nombre"],
                "area_id": area["id"],
                "area_direccion": "Planificación y Estadística",
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
                        "frecuencia": "anual",
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
        if not metas:
            sb.table("indicadores_metaperiodo").insert(
                [
                    {
                        "indicador_version_id": version["id"],
                        "meta_min": minimo,
                        "meta_max": None,
                        "fecha_inicio_meta": inicio,
                        "fecha_fin_meta": fin,
                    }
                    for inicio, fin, minimo in data["metas"]
                ]
            ).execute()
            print(f"  metas {', '.join(str(m[2]) for m in data['metas'])}")
        else:
            print(f"  metas ya existian ({len(metas)})")

        for anio, num, den, conclusion in data["mediciones"]:
            periodo = _periodo_anual(sb, anio)
            valor = _upsert_medicion(sb, version["id"], periodo, num, den, conclusion, admin["id"])
            print(f"  {periodo['label']}: {valor}% (VP)")


if __name__ == "__main__":
    main()
