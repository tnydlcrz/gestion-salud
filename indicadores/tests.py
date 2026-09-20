from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from cuentas.models import UsuarioArea
from cuentas.permissions import areas_visibles

from .models import (
    AreaDireccion,
    Dimension,
    Indicador,
    IndicadorVersion,
    Medicion,
    MetaPeriodo,
    Periodo,
)
from .forms import CantidadInput, MedicionForm
from .services import calcular_valor, semaforo, serie_desde_mediciones, texto_meta, texto_nd


class SemaforoTests(TestCase):
    def setUp(self):
        self.area = AreaDireccion.objects.create(nombre="Área test")
        self.dim = Dimension.objects.create(nombre="Gestión")
        self.indicador = Indicador.objects.create(
            nombre="Prueba", area=self.area, dimension=self.dim
        )
        self.version = IndicadorVersion.objects.create(
            indicador=self.indicador,
            version_num=1,
            fecha_vigencia_desde=date(2025, 1, 1),
            formula_calculo="x",
            tipo_calculo=IndicadorVersion.TipoCalculo.VALOR_DIRECTO,
            unidad_resultado="%",
            meta_tipo=IndicadorVersion.MetaTipo.MINIMO,
            sentido_mejora=IndicadorVersion.Sentido.ASCENDENTE,
            frecuencia="mensual",
        )
        self.meta = MetaPeriodo.objects.create(
            indicador_version=self.version,
            meta_min=Decimal("10"),
            meta_max=Decimal("20"),
            fecha_inicio_meta=date(2025, 1, 1),
            fecha_fin_meta=date(2026, 12, 31),
        )

    def test_minimo(self):
        self.assertEqual(semaforo(self.version, 10, self.meta), "verde")
        self.assertEqual(semaforo(self.version, 9, self.meta), "rojo")

    def test_maximo(self):
        self.version.meta_tipo = IndicadorVersion.MetaTipo.MAXIMO
        self.assertEqual(semaforo(self.version, 20, self.meta), "verde")
        self.assertEqual(semaforo(self.version, 21, self.meta), "rojo")

    def test_rango_y_sostener(self):
        self.version.meta_tipo = IndicadorVersion.MetaTipo.RANGO
        self.assertEqual(semaforo(self.version, 15, self.meta), "verde")
        self.assertEqual(semaforo(self.version, 21, self.meta), "rojo")
        self.version.meta_tipo = IndicadorVersion.MetaTipo.SOSTENER
        self.assertEqual(semaforo(self.version, 10, self.meta), "verde")

    def test_seguimiento_gris(self):
        self.version.meta_tipo = IndicadorVersion.MetaTipo.SEGUIMIENTO
        self.assertEqual(semaforo(self.version, 99, self.meta), "gris")

    def test_razon_porcentaje(self):
        self.version.tipo_calculo = IndicadorVersion.TipoCalculo.RAZON
        self.version.unidad_resultado = "%"
        self.assertEqual(calcular_valor(self.version, 35, 100), Decimal("35.0000"))

    def test_formulario_carga_sin_spinner_decimal(self):
        form = MedicionForm(version=self.version)
        widget = form.fields["numerador_valor"].widget
        self.assertIsInstance(widget, CantidadInput)
        self.assertNotEqual(widget.attrs.get("step"), "0.0001")
        self.assertEqual(widget.format_value(Decimal("10.0000")), "10")
        self.assertEqual(widget.format_value(Decimal("38.9000")), "38.9")

    def test_texto_meta(self):
        self.assertEqual(texto_meta(self.version, self.meta), "≥ 10 %")
        self.version.meta_tipo = IndicadorVersion.MetaTipo.MAXIMO
        self.assertEqual(texto_meta(self.version, self.meta), "≤ 20 %")

    def test_serie_colorea_puntos(self):
        periodo_ok = Periodo.objects.create(
            anio=2026, frecuencia="mensual", nro_periodo=1,
            fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 1, 31), label="Enero 2026",
        )
        periodo_mal = Periodo.objects.create(
            anio=2026, frecuencia="mensual", nro_periodo=2,
            fecha_inicio=date(2026, 2, 1), fecha_fin=date(2026, 2, 28), label="Febrero 2026",
        )
        ok = Medicion(
            indicador_version=self.version, periodo=periodo_ok, fecha_corte=date(2026, 1, 31),
            numerador_valor=Decimal("12"), estado=Medicion.Estado.PUBLICADO,
        )
        ok.calcular_valor()
        mal = Medicion(
            indicador_version=self.version, periodo=periodo_mal, fecha_corte=date(2026, 2, 28),
            numerador_valor=Decimal("8"), estado=Medicion.Estado.PUBLICADO,
        )
        mal.calcular_valor()
        serie = serie_desde_mediciones(self.version, [ok, mal])
        self.assertEqual(serie["colors"], ["#0f766e", "#b91c1c"])
        self.assertEqual(serie["detalles"][0]["n"], "12")
        self.assertEqual(serie["detalles"][0]["d"], "n/a")

    def test_nd_prueba_y_sin_dato(self):
        medicion = Medicion(
            indicador_version=self.version,
            numerador_valor=None,
            denominador_valor=None,
            es_prueba=True,
        )
        self.assertEqual(texto_nd(medicion, self.version), "N s/d · D n/a · VP")
        self.version.tipo_calculo = IndicadorVersion.TipoCalculo.RAZON
        medicion.numerador_valor = Decimal("68")
        medicion.denominador_valor = Decimal("95")
        medicion.es_prueba = False
        self.assertEqual(texto_nd(medicion, self.version), "N 68 · D 95")


class PermisoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.uep = AreaDireccion.objects.create(nombre="UEP")
        self.lab = AreaDireccion.objects.create(nombre="Lab")
        self.admin = User.objects.create_user(
            username="admin", email="admin@local", password="x", nombre="Admin", es_admin_global=True
        )
        self.area_user = User.objects.create_user(
            username="uep", email="uep@local", password="x", nombre="UEP"
        )
        UsuarioArea.objects.create(usuario=self.area_user, area=self.uep, rol=UsuarioArea.Rol.AREA)

    def test_admin_ve_todas(self):
        self.assertEqual(areas_visibles(self.admin).count(), 2)

    def test_area_solo_la_suya(self):
        nombres = list(areas_visibles(self.area_user).values_list("nombre", flat=True))
        self.assertEqual(nombres, ["UEP"])

    def test_home_filtra(self):
        self.client.force_login(self.area_user)
        resp = self.client.get(reverse("tablero:home"))
        self.assertContains(resp, "UEP")
        self.assertNotContains(resp, "Lab")

    def test_area_muestra_graficos(self):
        dim = Dimension.objects.create(nombre="Gestión")
        indicador = Indicador.objects.create(nombre="Indicador mosaico", area=self.uep, dimension=dim)
        version = IndicadorVersion.objects.create(
            indicador=indicador,
            version_num=1,
            fecha_vigencia_desde=date(2025, 1, 1),
            formula_calculo="x",
            tipo_calculo=IndicadorVersion.TipoCalculo.VALOR_DIRECTO,
            unidad_resultado="casos",
            meta_tipo=IndicadorVersion.MetaTipo.MINIMO,
            sentido_mejora=IndicadorVersion.Sentido.ASCENDENTE,
            frecuencia="mensual",
        )
        MetaPeriodo.objects.create(
            indicador_version=version,
            meta_min=Decimal("10"),
            fecha_inicio_meta=date(2025, 1, 1),
            fecha_fin_meta=date(2026, 12, 31),
        )
        self.client.force_login(self.area_user)
        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get(reverse("tablero:area", args=[self.uep.pk]))
        self.assertContains(resp, "Indicador mosaico")
        self.assertContains(resp, f'id="chart-{indicador.pk}"')
        self.assertContains(resp, "chart.umd.min.js")
        self.assertContains(resp, "Meta")
        self.assertContains(resp, "s/d")
        self.assertLessEqual(len(ctx.captured_queries), 15)
