from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from cuentas.models import UsuarioArea
from indicadores.models import (
    AreaDireccion,
    Dimension,
    Frecuencia,
    Indicador,
    IndicadorVersion,
    Medicion,
    MetaPeriodo,
    Periodo,
    Responsable,
)

PASSWORD = "tablero2026"

DIMENSIONES = [
    "Gestión Específica del Área",
    "Capacitaciones",
    "Producción/Gestión Administrativa y/o Presupuestaria",
    "Intervenciones Comunitarias y Cobertura Territorial",
    "Resultados",
    "Estructural (capacidad instalada)",
    "Procesos (soporte interno)",
]

PERIODOS_POR_FREQ = {
    Frecuencia.MENSUAL: 12,
    Frecuencia.TRIMESTRAL: 4,
    Frecuencia.CUATRIMESTRAL: 3,
    Frecuencia.SEMESTRAL: 2,
    Frecuencia.ANUAL: 1,
}

LABELS = {
    Frecuencia.MENSUAL: [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ],
    Frecuencia.TRIMESTRAL: ["1er trimestre", "2º trimestre", "3er trimestre", "4º trimestre"],
    Frecuencia.CUATRIMESTRAL: ["1er cuatrimestre", "2º cuatrimestre", "3er cuatrimestre"],
    Frecuencia.SEMESTRAL: ["1er semestre", "2º semestre"],
    Frecuencia.ANUAL: ["Año"],
}


def _rango(anio, frecuencia, nro):
    if frecuencia == Frecuencia.MENSUAL:
        ini = date(anio, nro, 1)
        return ini, date(anio, nro, monthrange(anio, nro)[1])
    if frecuencia == Frecuencia.TRIMESTRAL:
        mes = 1 + (nro - 1) * 3
        ini = date(anio, mes, 1)
        fin_mes = mes + 2
        return ini, date(anio, fin_mes, monthrange(anio, fin_mes)[1])
    if frecuencia == Frecuencia.CUATRIMESTRAL:
        mes = 1 + (nro - 1) * 4
        ini = date(anio, mes, 1)
        fin_mes = mes + 3
        return ini, date(anio, fin_mes, monthrange(anio, fin_mes)[1])
    if frecuencia == Frecuencia.SEMESTRAL:
        mes = 1 if nro == 1 else 7
        ini = date(anio, mes, 1)
        fin_mes = 6 if nro == 1 else 12
        return ini, date(anio, fin_mes, monthrange(anio, fin_mes)[1])
    return date(anio, 1, 1), date(anio, 12, 31)


def _label(anio, frecuencia, nro):
    return f"{LABELS[frecuencia][nro - 1]} {anio}"


def _periodos():
    creados = {}
    for anio in (2025, 2026):
        for freq, cantidad in PERIODOS_POR_FREQ.items():
            for nro in range(1, cantidad + 1):
                ini, fin = _rango(anio, freq, nro)
                obj, _ = Periodo.objects.get_or_create(
                    anio=anio,
                    frecuencia=freq,
                    nro_periodo=nro,
                    defaults={
                        "fecha_inicio": ini,
                        "fecha_fin": fin,
                        "label": _label(anio, freq, nro),
                    },
                )
                creados[(anio, freq, nro)] = obj
    return creados


def _indicador(area, dimension, responsable, admin, data, periodos):
    indicador, _ = Indicador.objects.get_or_create(
        nombre=data["nombre"],
        area=area,
        defaults={
            "dimension": dimension,
            "responsable": responsable,
            "creado_por": admin,
            "actualizado_por": admin,
            "area_direccion": data.get("area_direccion", ""),
        },
    )
    if data.get("area_direccion") and indicador.area_direccion != data["area_direccion"]:
        indicador.area_direccion = data["area_direccion"]
        indicador.save(update_fields=["area_direccion"])
    version = indicador.version_vigente()
    if not version:
        version = IndicadorVersion.objects.create(
            indicador=indicador,
            version_num=1,
            fecha_vigencia_desde=date(2025, 1, 1),
            formula_calculo=data["formula"],
            tipo_calculo=data["tipo_calculo"],
            numerador_descripcion=data.get("num_desc", ""),
            numerador_unidad=data.get("num_unidad", ""),
            denominador_descripcion=data.get("den_desc", ""),
            denominador_unidad=data.get("den_unidad", ""),
            unidad_resultado=data["unidad"],
            meta_tipo=data["meta_tipo"],
            sentido_mejora=data["sentido"],
            fuente_datos=data["fuente"],
            frecuencia=data["frecuencia"],
            objetivo_operativo=data.get("objetivo", ""),
            nota_metodologica=data.get("nota", ""),
        )
        MetaPeriodo.objects.create(
            indicador_version=version,
            meta_min=data.get("meta_min"),
            meta_max=data.get("meta_max"),
            fecha_inicio_meta=date(2025, 1, 1),
            fecha_fin_meta=date(2026, 12, 31),
        )
    for med in data.get("mediciones", []):
        periodo = periodos[med["periodo"]]
        defaults = {
            "fecha_corte": periodo.fecha_fin,
            "numerador_valor": med.get("num"),
            "denominador_valor": med.get("den"),
            "conclusion": med.get("conclusion", ""),
            "es_prueba": med.get(
                "es_prueba",
                "prueba" in med.get("conclusion", "").lower(),
            ),
            "estado": Medicion.Estado.PUBLICADO,
            "usuario_carga": admin,
        }
        if med.get("valor") is not None and data["tipo_calculo"] == IndicadorVersion.TipoCalculo.VALOR_DIRECTO:
            defaults["numerador_valor"] = med["valor"]
        Medicion.objects.update_or_create(
            indicador_version=version,
            periodo=periodo,
            defaults=defaults,
        )
    return indicador


class Command(BaseCommand):
    help = "Carga áreas, usuarios de prueba y los indicadores del MVP."

    def add_arguments(self, parser):
        parser.add_argument(
            "--si-vacio",
            action="store_true",
            help="Omite la carga si ya existen áreas (útil en cada arranque del piloto).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["si_vacio"] and AreaDireccion.objects.exists():
            self.stdout.write("Seed omitido: el tablero ya tiene áreas.")
            return

        User = get_user_model()
        dims = {nombre: Dimension.objects.get_or_create(nombre=nombre)[0] for nombre in DIMENSIONES}
        uep, _ = AreaDireccion.objects.get_or_create(nombre="Unidad Ejecutora Provincial")
        lab, _ = AreaDireccion.objects.get_or_create(nombre="Laboratorio Central de Redes y Programas")
        sumar, _ = AreaDireccion.objects.get_or_create(nombre="SUMAR+")
        sistemas, _ = AreaDireccion.objects.get_or_create(nombre="Dirección de Sistemas")

        resp_uep, _ = Responsable.objects.get_or_create(
            area=uep, nombre="Responsable UEP", defaults={"correo": "uep@salud.corrientes.gob.ar"}
        )
        resp_lab, _ = Responsable.objects.get_or_create(
            area=lab, nombre="Responsable LCRyP", defaults={"correo": "lab@salud.corrientes.gob.ar"}
        )
        resp_sumar, _ = Responsable.objects.get_or_create(
            area=sumar, nombre="Responsable SUMAR+", defaults={"correo": "sumar@salud.corrientes.gob.ar"}
        )
        resp_sistemas, _ = Responsable.objects.get_or_create(
            area=sistemas, nombre="Responsable Dirección de Sistemas", defaults={"correo": "sistemas@salud.corrientes.gob.ar"}
        )

        admin, _ = User.objects.get_or_create(
            email="admin@local",
            defaults={
                "username": "admin",
                "nombre": "Administración del tablero",
                "es_admin_global": True,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin.set_password(PASSWORD)
        admin.es_admin_global = True
        admin.is_staff = True
        admin.is_superuser = True
        admin.save()

        user_uep, _ = User.objects.get_or_create(
            email="uep@local",
            defaults={"username": "uep", "nombre": "Referente UEP"},
        )
        user_uep.set_password(PASSWORD)
        user_uep.save()
        user_lab, _ = User.objects.get_or_create(
            email="lab@local",
            defaults={"username": "lab", "nombre": "Referente Laboratorio Central"},
        )
        user_lab.set_password(PASSWORD)
        user_lab.save()
        user_sumar, _ = User.objects.get_or_create(
            email="sumar@local",
            defaults={"username": "sumar", "nombre": "Referente SUMAR+"},
        )
        user_sumar.set_password(PASSWORD)
        user_sumar.save()
        user_sistemas, _ = User.objects.get_or_create(
            email="sistemas@local",
            defaults={"username": "sistemas", "nombre": "Referente Dirección de Sistemas"},
        )
        user_sistemas.set_password(PASSWORD)
        user_sistemas.save()

        UsuarioArea.objects.get_or_create(
            usuario=user_uep, area=uep, fecha_baja=None, defaults={"rol": UsuarioArea.Rol.AREA, "otorgado_por": admin}
        )
        UsuarioArea.objects.get_or_create(
            usuario=user_lab, area=lab, fecha_baja=None, defaults={"rol": UsuarioArea.Rol.AREA, "otorgado_por": admin}
        )
        UsuarioArea.objects.get_or_create(
            usuario=user_sumar, area=sumar, fecha_baja=None, defaults={"rol": UsuarioArea.Rol.AREA, "otorgado_por": admin}
        )
        UsuarioArea.objects.get_or_create(
            usuario=user_sistemas, area=sistemas, fecha_baja=None, defaults={"rol": UsuarioArea.Rol.AREA, "otorgado_por": admin}
        )

        periodos = _periodos()
        M, T, S, A = Frecuencia.MENSUAL, Frecuencia.TRIMESTRAL, Frecuencia.SEMESTRAL, Frecuencia.ANUAL

        uep_defs = [
            {
                "nombre": "Capacitación en Facturación a OS a Efectores de Salud",
                "area_direccion": "UEP-UGP-MSP",
                "dimension": "Gestión Específica del Área",
                "formula": "Cantidad de capacitaciones externas realizadas en el mes",
                "tipo_calculo": IndicadorVersion.TipoCalculo.VALOR_DIRECTO,
                "unidad": "capacitaciones",
                "num_desc": "Capacitaciones externas realizadas",
                "num_unidad": "cantidad",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Registro de Capacitaciones Externas Realizadas",
                "frecuencia": M,
                "objetivo": "Mantener las capacitaciones externas realizadas a Efectores de Salud",
                "meta_min": Decimal("10"),
                "mediciones": [
                    {"periodo": (2025, M, 9), "valor": Decimal("8"), "conclusion": "Por debajo de la meta mensual."},
                    {"periodo": (2025, M, 10), "valor": Decimal("10"), "conclusion": "Se alcanzó la meta de 10 capacitaciones."},
                    {"periodo": (2025, M, 11), "valor": Decimal("12"), "conclusion": "Se superó la meta con cobertura a más efectores."},
                    {"periodo": (2026, M, 3), "valor": Decimal("9"), "conclusion": "Una capacitación reprogramada por agenda de efectores."},
                ],
            },
            {
                "nombre": "Índice de Recupero de Deuda",
                "area_direccion": "UEP-UGP-MSP",
                "dimension": "Gestión Específica del Área",
                "formula": "Monto cobrado en el periodo / Total deudas vencidas",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Monto cobrado en el período",
                "num_unidad": "$",
                "den_desc": "Total deudas vencidas",
                "den_unidad": "$",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "F-GC-01 Informe de Deuda",
                "frecuencia": M,
                "objetivo": "Incrementar el recupero de deuda vencida",
                "meta_min": Decimal("35"),
                "mediciones": [
                    {"periodo": (2025, M, 9), "num": Decimal("280"), "den": Decimal("1000"), "conclusion": "28%: por debajo del 35%."},
                    {"periodo": (2025, M, 10), "num": Decimal("350"), "den": Decimal("1000"), "conclusion": "Se alcanzó la meta del 35%."},
                    {"periodo": (2025, M, 11), "num": Decimal("410"), "den": Decimal("1000"), "conclusion": "Mejora del circuito de cobranza."},
                    {"periodo": (2026, M, 3), "num": Decimal("320"), "den": Decimal("1000"), "conclusion": "32%: aún bajo la meta mensual."},
                ],
            },
            {
                "nombre": "Cumplimiento del Plan Anual de Capacitaciones Internas",
                "area_direccion": "UEP-UGP-MSP",
                "dimension": "Capacitaciones",
                "formula": "Cantidad de capacitaciones programadas realizadas / Cantidad de capacitaciones programadas × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Capacitaciones del PAC realizadas",
                "num_unidad": "cantidad",
                "den_desc": "Capacitaciones programadas en el PAC",
                "den_unidad": "cantidad",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "F-RRHH-05 PAC y F-RRHH-06 Registro de Asistencia",
                "frecuencia": A,
                "objetivo": "Aumentar la transferencia de competencias en los puestos de trabajo de los agentes de la UEP",
                "meta_min": Decimal("100"),
                "mediciones": [
                    {
                        "periodo": (2025, A, 1),
                        "num": Decimal("5"),
                        "den": Decimal("7"),
                        "conclusion": "5 de 7 capacitaciones del PAC 2025. Faltaron dos actividades del segundo semestre.",
                    },
                ],
            },
            {
                "nombre": "Tiempo promedio de pago a Efectores Públicos",
                "area_direccion": "UEP-UGP-MSP",
                "dimension": "Producción/Gestión Administrativa y/o Presupuestaria",
                "formula": "Tiempo promedio (días entre cobranza hasta pago del total de expedientes del mes)",
                "tipo_calculo": IndicadorVersion.TipoCalculo.VALOR_DIRECTO,
                "unidad": "días",
                "num_desc": "Días promedio cobranza–pago",
                "num_unidad": "días",
                "meta_tipo": IndicadorVersion.MetaTipo.MAXIMO,
                "sentido": IndicadorVersion.Sentido.DESCENDENTE,
                "fuente": "Sistema de liquidación y Registro de Tesorería",
                "frecuencia": M,
                "objetivo": "Disminuir los plazos de pagos a Efectores Públicos",
                "meta_max": Decimal("30"),
                "mediciones": [
                    {"periodo": (2025, M, 9), "valor": Decimal("35"), "conclusion": "35 días: por encima del máximo de 30."},
                    {"periodo": (2025, M, 10), "valor": Decimal("28"), "conclusion": "Dentro del plazo máximo."},
                    {"periodo": (2025, M, 11), "valor": Decimal("22"), "conclusion": "Mejora del circuito de tesorería."},
                    {"periodo": (2026, M, 3), "valor": Decimal("31"), "conclusion": "Un día por encima de la meta."},
                ],
            },
            {
                "nombre": "Incremento Facturación Mensual",
                "area_direccion": "UEP-UGP-MSP",
                "dimension": "Intervenciones Comunitarias y Cobertura Territorial",
                "formula": "(Facturación mes actual – Facturación mes anterior) / Facturación mes anterior × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Variación de facturación (actual − anterior)",
                "num_unidad": "$",
                "den_desc": "Facturación del mes anterior",
                "den_unidad": "$",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Sistema ADM IMEDIC",
                "frecuencia": M,
                "objetivo": "Incrementar la facturación realizada por los Efectores Públicos",
                "meta_min": Decimal("5"),
                "mediciones": [
                    {"periodo": (2025, M, 9), "num": Decimal("3"), "den": Decimal("100"), "conclusion": "3%: por debajo del 5% mensual."},
                    {"periodo": (2025, M, 10), "num": Decimal("6"), "den": Decimal("100"), "conclusion": "Se superó la meta."},
                    {"periodo": (2025, M, 11), "num": Decimal("8"), "den": Decimal("100"), "conclusion": "Repunte de facturación en efectores."},
                    {"periodo": (2026, M, 3), "num": Decimal("4"), "den": Decimal("100"), "conclusion": "4%: no se alcanza el 5%."},
                ],
            },
        ]

        lab_defs = [
            {
                "nombre": "Tasa de resolución interna de prácticas de alta complejidad",
                "dimension": "Gestión Específica del Área",
                "formula": "(N° de prácticas de alta complejidad resueltas en el LCRyP ÷ N° total de prácticas de alta complejidad solicitadas) × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Prácticas de alta complejidad resueltas en el LCRyP",
                "den_desc": "Prácticas de alta complejidad solicitadas",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Sistema de gestión de derivaciones / LIS",
                "frecuencia": T,
                "meta_min": Decimal("90"),
                "mediciones": [
                    {"periodo": (2025, T, 4), "num": Decimal("93"), "den": Decimal("100"), "conclusion": "93% (2025). El laboratorio supera la meta, resolviendo internamente la gran mayoría de las prácticas de alta complejidad."},
                    {"periodo": (2026, T, 2), "num": Decimal("93"), "den": Decimal("100"), "conclusion": "93% (2026). Se sostiene el cumplimiento por encima del 90%."},
                ],
            },
            {
                "nombre": "Cobertura de formación continua del personal",
                "dimension": "Capacitaciones",
                "formula": "(N° de agentes con participación registrada en capacitación ÷ Dotación total, por categoría) × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Agentes con participación registrada",
                "den_desc": "Dotación total",
                "meta_tipo": IndicadorVersion.MetaTipo.RANGO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Registro de actividades de capacitación / legajo electrónico",
                "frecuencia": A,
                "meta_min": Decimal("75"),
                "meta_max": Decimal("90"),
                "mediciones": [
                    {
                        "periodo": (2025, A, 1),
                        "num": Decimal("33.9"),
                        "den": Decimal("100"),
                        "conclusion": "33,9% general (2025). Bioquímicos 83,3%; técnicos 28,6%. La participación general está bajo la banda 75–90%, con brecha marcada entre categorías.",
                    },
                ],
            },
            {
                "nombre": "Tasa de recupero de gastos por cobertura de salud",
                "dimension": "Producción/Gestión Administrativa y/o Presupuestaria",
                "formula": "(N° de prácticas con cobertura recuperable ÷ Total de prácticas realizadas) × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Prácticas con cobertura recuperable",
                "den_desc": "Total de prácticas realizadas",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Sistema de facturación / UEP-UGP",
                "frecuencia": S,
                "meta_min": Decimal("70"),
                "mediciones": [
                    {"periodo": (2025, S, 1), "num": Decimal("64.6"), "den": Decimal("100"), "conclusion": "64,6% en el primer semestre 2025: por debajo del 70%."},
                    {"periodo": (2026, S, 1), "num": Decimal("60.3"), "den": Decimal("100"), "conclusion": "60,3% (2026). El circuito de facturación y cobro necesita fortalecerse."},
                ],
            },
            {
                "nombre": "Tiempo promedio de giro de expedientes de compra a orden de compra",
                "dimension": "Producción/Gestión Administrativa y/o Presupuestaria",
                "formula": "∑ (fecha de emisión de orden de compra − fecha de presentación de expedientes) ÷ número de expedientes iniciados",
                "tipo_calculo": IndicadorVersion.TipoCalculo.VALOR_DIRECTO,
                "unidad": "días/expte",
                "num_desc": "Días promedio por expediente",
                "num_unidad": "días",
                "meta_tipo": IndicadorVersion.MetaTipo.MAXIMO,
                "sentido": IndicadorVersion.Sentido.DESCENDENTE,
                "fuente": "Registro de expedientes, cuadros comparativos, órdenes de compra",
                "frecuencia": S,
                "meta_min": None,
                "meta_max": Decimal("30"),
                "mediciones": [
                    {"periodo": (2025, S, 1), "valor": Decimal("61.4"), "conclusion": "61,4 días/expte (2025). El circuito con intervención ministerial excede la meta."},
                    {"periodo": (2026, S, 1), "valor": Decimal("38.9"), "conclusion": "38,9 días/expte (2026). Notable disminución, todavía por encima de 30 días."},
                ],
            },
            {
                "nombre": "Cobertura de operativos de procuración y trasplante (Provincia de Corrientes)",
                "dimension": "Intervenciones Comunitarias y Cobertura Territorial",
                "formula": "(N° de operativos atendidos ÷ N° de operativos solicitados) × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Operativos atendidos",
                "den_desc": "Operativos solicitados",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "SINTRA / Registro CUCAICOR",
                "frecuencia": A,
                "meta_min": Decimal("100"),
                "mediciones": [
                    {
                        "periodo": (2025, A, 1),
                        "num": Decimal("100"),
                        "den": Decimal("100"),
                        "conclusion": "100% (2025). El laboratorio atendió la totalidad de los operativos solicitados.",
                    },
                ],
            },
            {
                "nombre": "Índice de complejidad analítica de la cartera de prestaciones",
                "dimension": "Resultados",
                "formula": "(N° de prácticas de alta complejidad ÷ Total de prácticas realizadas) × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Prácticas de alta complejidad",
                "den_desc": "Total de prácticas realizadas",
                "meta_tipo": IndicadorVersion.MetaTipo.SOSTENER,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "LIS / Dashboard de Prácticas por Obra Social Valorizado",
                "frecuencia": T,
                "meta_min": Decimal("45"),
                "mediciones": [
                    {"periodo": (2025, T, 3), "num": Decimal("45.8"), "den": Decimal("100"), "conclusion": "45,8% (junio–agosto 2025). Se cumplió la meta de sostener ≥ 45%."},
                    {"periodo": (2026, T, 2), "num": Decimal("45"), "den": Decimal("100"), "conclusion": "45% (2026). Se sostiene el piso de complejidad analítica."},
                ],
            },
        ]

        sumar_defs = [
            {
                "nombre": "Cobertura efectiva Básica",
                "area_direccion": "Planificación Operativa y Monitoreo",
                "dimension": "Intervenciones Comunitarias y Cobertura Territorial",
                "formula": "Número total de Beneficiarios con Cobertura Pública específica (CEB) / Población elegible del programa",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Beneficiarios con cobertura pública específica (CEB)",
                "den_desc": "Población elegible del programa",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Padrón de beneficiarios Sumar+",
                "frecuencia": M,
                "nota": "Valores 2026 de prueba.",
                "meta_min": Decimal("39"),
                "mediciones": [
                    {"periodo": (2026, M, 1), "num": Decimal("36"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026. Pendiente de reemplazo con dato real."},
                    {"periodo": (2026, M, 2), "num": Decimal("37.5"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 3), "num": Decimal("39.2"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026. Alcanza la meta del 39%."},
                    {"periodo": (2026, M, 4), "num": Decimal("38"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 5), "num": Decimal("40.1"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 6), "num": Decimal("41"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                ],
            },
            {
                "nombre": "Porcentaje de efectores facturantes",
                "area_direccion": "Sistemas-Facturación-Legales",
                "dimension": "Gestión Específica del Área",
                "formula": "Efectores con convenio con prestaciones facturadas en el último trimestre / Efectores con convenio de gestión firmado",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Efectores con convenio y prestaciones facturadas en el trimestre",
                "den_desc": "Efectores con convenio de gestión firmado",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Sistema de facturación / Tabla de efectores",
                "frecuencia": T,
                "nota": "Valores 2026 de prueba.",
                "meta_min": Decimal("70"),
                "mediciones": [
                    {"periodo": (2026, T, 1), "num": Decimal("68"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026. Por debajo del 70%."},
                    {"periodo": (2026, T, 2), "num": Decimal("73"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026. Superó la meta."},
                ],
            },
            {
                "nombre": "Porcentaje de efectores con convenio",
                "area_direccion": "Legales",
                "dimension": "Producción/Gestión Administrativa y/o Presupuestaria",
                "formula": "Cantidad de efectores con convenio / Cantidad total de efectores integrantes",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Efectores con convenio",
                "den_desc": "Efectores integrantes",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Tabla de efectores",
                "frecuencia": M,
                "nota": "Valores 2026 de prueba.",
                "meta_min": Decimal("70"),
                "mediciones": [
                    {"periodo": (2026, M, 1), "num": Decimal("71"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 2), "num": Decimal("72"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 3), "num": Decimal("69"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026. Un punto bajo la meta."},
                    {"periodo": (2026, M, 4), "num": Decimal("74"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 5), "num": Decimal("75"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 6), "num": Decimal("76"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                ],
            },
            {
                "nombre": "Plazo de Pago a los efectores",
                "area_direccion": "Administración",
                "dimension": "Producción/Gestión Administrativa y/o Presupuestaria",
                "formula": "Promedio de fechas de recepción de facturas pagadas en el mes − promedio de las fechas de pago",
                "tipo_calculo": IndicadorVersion.TipoCalculo.VALOR_DIRECTO,
                "unidad": "días",
                "num_desc": "Días promedio recepción–pago",
                "num_unidad": "días",
                "meta_tipo": IndicadorVersion.MetaTipo.MAXIMO,
                "sentido": IndicadorVersion.Sentido.DESCENDENTE,
                "fuente": "Transferencias a efectores",
                "frecuencia": M,
                "nota": "Valores 2026 de prueba.",
                "meta_max": Decimal("50"),
                "mediciones": [
                    {"periodo": (2026, M, 1), "valor": Decimal("54"), "conclusion": "Valor de prueba 2026. Por encima de 50 días."},
                    {"periodo": (2026, M, 2), "valor": Decimal("51"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 3), "valor": Decimal("48"), "conclusion": "Valor de prueba 2026. Dentro de la meta."},
                    {"periodo": (2026, M, 4), "valor": Decimal("47"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 5), "valor": Decimal("49"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 6), "valor": Decimal("46"), "conclusion": "Valor de prueba 2026."},
                ],
            },
        ]

        sistemas_defs = [
            {
                "nombre": "Uso Efectivo del Sistema HCE",
                "area_direccion": "Dirección de Sistemas",
                "dimension": "Gestión Específica del Área",
                "formula": "Usuarios con al menos un ingreso al sistema en los últimos 6 meses / Total de usuarios habilitados × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Usuarios con al menos un ingreso en los últimos 6 meses",
                "den_desc": "Total de usuarios habilitados",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Sistema de Historia Clínica Electrónica",
                "frecuencia": M,
                "nota": "Línea de base prevista a partir del padrón de usuarios HCE. Valores 2026 de prueba.",
                "meta_min": Decimal("75"),
                "mediciones": [
                    {"periodo": (2026, M, 1), "num": Decimal("68"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 2), "num": Decimal("71"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 3), "num": Decimal("74"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 4), "num": Decimal("76"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026. Alcanza la meta del 75%."},
                    {"periodo": (2026, M, 5), "num": Decimal("78"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 6), "num": Decimal("77"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                ],
            },
            {
                "nombre": "Resolución de Incidencias con Proveedor",
                "area_direccion": "Dirección de Sistemas",
                "dimension": "Gestión Específica del Área",
                "formula": "Incidencias/solicitudes resueltas dentro del plazo comprometido / Total de incidencias reportadas al proveedor × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Incidencias resueltas en plazo",
                "den_desc": "Total de incidencias reportadas al proveedor",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Registro propio de seguimiento de solicitudes (correo / planilla de backlog)",
                "frecuencia": M,
                "nota": "Valores 2026 de prueba.",
                "meta_min": Decimal("80"),
                "mediciones": [
                    {"periodo": (2026, M, 1), "num": Decimal("72"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 2), "num": Decimal("78"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 3), "num": Decimal("81"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 4), "num": Decimal("83"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 5), "num": Decimal("79"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 6), "num": Decimal("84"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                ],
            },
            {
                "nombre": "Cobertura de Capacitación en HCE",
                "area_direccion": "Dirección de Sistemas",
                "dimension": "Capacitaciones",
                "formula": "Agentes que completaron capacitación en carga de Historia Clínica Electrónica / Total de agentes con usuario asignado × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Agentes que completaron capacitación en carga de HCE",
                "den_desc": "Total de agentes con usuario asignado",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Planillas de asistencia a capacitaciones",
                "frecuencia": S,
                "nota": "Valores 2026 de prueba.",
                "meta_min": Decimal("75"),
                "mediciones": [
                    {"periodo": (2026, S, 1), "num": Decimal("61"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026. Por debajo de la meta del 75%."},
                ],
            },
            {
                "nombre": "Consistencia de Datos entre Fuentes",
                "area_direccion": "Dirección de Sistemas",
                "dimension": "Producción/Gestión Administrativa y/o Presupuestaria",
                "formula": "Establecimientos/reportes sin discrepancias entre fuentes (sistema HCE, SIIS, Power BI) / Total de establecimientos auditados × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Establecimientos/reportes sin discrepancias",
                "den_desc": "Total de establecimientos auditados",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Cruce de reportes: sistema HCE, SIIS Formulario 2.1, Power BI",
                "frecuencia": T,
                "nota": "Discrepancias ya identificadas entre HCE, SIIS y Power BI. Valores 2026 de prueba.",
                "meta_min": Decimal("75"),
                "mediciones": [
                    {"periodo": (2026, T, 1), "num": Decimal("58"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026. Pendiente de resolución con el proveedor."},
                    {"periodo": (2026, T, 2), "num": Decimal("64"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                ],
            },
            {
                "nombre": "Establecimientos con HCE Operativa",
                "area_direccion": "Dirección de Sistemas",
                "dimension": "Intervenciones Comunitarias y Cobertura Territorial",
                "formula": "Establecimientos (CAPS + hospitales) con HCE activa y con registro de actividad en el mes / Total de establecimientos de la red × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Establecimientos con HCE activa y actividad en el mes",
                "den_desc": "Total de establecimientos de la red",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Sistema de Historia Clínica Electrónica",
                "frecuencia": M,
                "nota": "Valores 2026 de prueba.",
                "meta_min": Decimal("95"),
                "mediciones": [
                    {"periodo": (2026, M, 1), "num": Decimal("88"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 2), "num": Decimal("90"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 3), "num": Decimal("92"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 4), "num": Decimal("94"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 5), "num": Decimal("95"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026. Alcanza la meta."},
                    {"periodo": (2026, M, 6), "num": Decimal("96"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                ],
            },
            {
                "nombre": "Disponibilidad de Usuarios Habilitados por Establecimiento",
                "area_direccion": "Dirección de Sistemas",
                "dimension": "Estructural (capacidad instalada)",
                "formula": "Establecimientos de la red con al menos un usuario HCE habilitado / Total de establecimientos de la red × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Establecimientos con al menos un usuario HCE habilitado",
                "den_desc": "Total de establecimientos de la red",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Sistema de Historia Clínica Electrónica",
                "frecuencia": T,
                "nota": "Resguardo estructural. Línea de base a partir del padrón HCE. Valores 2026 de prueba.",
                "meta_min": Decimal("85"),
                "mediciones": [
                    {"periodo": (2026, T, 1), "num": Decimal("81"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, T, 2), "num": Decimal("86"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                ],
            },
            {
                "nombre": "Tiempo de Atención de Solicitudes de Soporte Interno",
                "area_direccion": "Dirección de Sistemas",
                "dimension": "Procesos (soporte interno)",
                "formula": "Solicitudes de soporte de otras áreas del Ministerio atendidas dentro de las 72hs / Total de solicitudes recibidas × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Solicitudes atendidas dentro de 72 horas",
                "den_desc": "Total de solicitudes recibidas",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Registro de tickets / mesa de ayuda interna",
                "frecuencia": M,
                "nota": "Resguardo de procesos. Valores 2026 de prueba.",
                "meta_min": Decimal("95"),
                "mediciones": [
                    {"periodo": (2026, M, 1), "num": Decimal("91"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 2), "num": Decimal("93"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 3), "num": Decimal("96"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 4), "num": Decimal("94"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 5), "num": Decimal("97"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 6), "num": Decimal("95"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                ],
            },
            {
                "nombre": "Disponibilidad de Conectividad de Red",
                "area_direccion": "Dirección de Sistemas",
                "dimension": "Estructural (capacidad instalada)",
                "formula": "Nodos con conectividad activa y operativa en el mes / Total de nodos contratados con el proveedor de conectividad × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Nodos con conectividad activa y operativa",
                "den_desc": "Total de nodos contratados",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Anexo de Servicio de Conectividad Mensual (proveedor de telecomunicaciones)",
                "frecuencia": M,
                "nota": "Incorporado a partir del relevamiento de infraestructura. Valores 2026 de prueba.",
                "meta_min": Decimal("95"),
                "mediciones": [
                    {"periodo": (2026, M, 1), "num": Decimal("91"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 2), "num": Decimal("93"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 3), "num": Decimal("94"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 4), "num": Decimal("96"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 5), "num": Decimal("95"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                    {"periodo": (2026, M, 6), "num": Decimal("97"), "den": Decimal("100"), "conclusion": "Valor de prueba 2026."},
                ],
            },
            {
                "nombre": "Cobertura de Ancho de Banda Adecuado",
                "area_direccion": "Dirección de Sistemas",
                "dimension": "Estructural (capacidad instalada)",
                "formula": "Nodos con ancho de banda igual o superior a 40 Mb (fibra óptica o simétrica) / Total de nodos con conectividad × 100",
                "tipo_calculo": IndicadorVersion.TipoCalculo.RAZON,
                "unidad": "%",
                "num_desc": "Nodos con 40 Mb o más",
                "den_desc": "Total de nodos con conectividad",
                "meta_tipo": IndicadorVersion.MetaTipo.MINIMO,
                "sentido": IndicadorVersion.Sentido.ASCENDENTE,
                "fuente": "Anexo de Servicio de Conectividad Mensual, tabla de tecnología/ancho de banda",
                "frecuencia": T,
                "nota": "Línea de base del documento: 68 de 95 nodos (72%) con fibra simétrica de 40 Mb o más.",
                "meta_min": Decimal("75"),
                "mediciones": [
                    {"periodo": (2026, T, 1), "num": Decimal("68"), "den": Decimal("95"), "conclusion": "Línea de base del documento: 68/95 nodos (72%). Por debajo de la meta del 75%."},
                    {"periodo": (2026, T, 2), "num": Decimal("70"), "den": Decimal("95"), "conclusion": "Valor de prueba 2026. Mejora respecto de la línea de base."},
                ],
            },
        ]

        for data in uep_defs:
            _indicador(uep, dims[data["dimension"]], resp_uep, admin, data, periodos)
        for data in lab_defs:
            _indicador(lab, dims[data["dimension"]], resp_lab, admin, data, periodos)
        for data in sumar_defs:
            _indicador(sumar, dims[data["dimension"]], resp_sumar, admin, data, periodos)
        for data in sistemas_defs:
            _indicador(sistemas, dims[data["dimension"]], resp_sistemas, admin, data, periodos)

        self.stdout.write(self.style.SUCCESS(
            "Seed listo. Usuarios: admin@local / uep@local / lab@local / sumar@local / sistemas@local  —  clave: tablero2026"
        ))
