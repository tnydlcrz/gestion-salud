import json

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import DetailView, FormView, TemplateView

from cuentas.permissions import areas_visibles, puede_cargar_area, puede_ver_area

from .forms import MedicionForm
from .models import AreaDireccion, Indicador, Medicion
from .services import (
    indicadores_precargados,
    meta_para,
    resumen_area,
    resumenes_areas,
    semaforo,
    serie_chart,
    serie_desde_mediciones,
    texto_nd,
    ultima_medicion_publicada,
)


class AreaPermisoMixin(LoginRequiredMixin):
    def area_objeto(self):
        raise NotImplementedError

    def dispatch(self, request, *args, **kwargs):
        area = self.area_objeto()
        if not puede_ver_area(request.user, area):
            raise Http404()
        return super().dispatch(request, *args, **kwargs)


class CachedObjectMixin:
    def get_object(self, queryset=None):
        if not hasattr(self, "_cached_object"):
            self._cached_object = super().get_object(queryset)
        return self._cached_object


class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "tablero/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["resumenes"] = resumenes_areas(areas_visibles(self.request.user))
        return ctx


class AreaDetailView(AreaPermisoMixin, CachedObjectMixin, DetailView):
    model = AreaDireccion
    template_name = "tablero/area.html"
    context_object_name = "area"

    def area_objeto(self):
        return self.get_object()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        resumen = resumen_area(self.object)
        por_dimension = {}
        for fila in resumen["filas"]:
            indicador = fila["indicador"]
            fila["version"] = indicador.version_vigente()
            fila["chart"] = json.dumps(serie_chart(indicador))
            fila["chart_id"] = f"chart-{indicador.pk}"
            por_dimension.setdefault(indicador.dimension, []).append(fila)
        ctx["resumen"] = resumen
        ctx["por_dimension"] = por_dimension
        return ctx


class IndicadorDetailView(AreaPermisoMixin, CachedObjectMixin, DetailView):
    model = Indicador
    template_name = "tablero/ficha.html"
    context_object_name = "indicador"

    def get_queryset(self):
        return indicadores_precargados()

    def area_objeto(self):
        return self.get_object().area

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        version = self.object.version_vigente()
        anio = self.request.GET.get("anio")
        mediciones = []
        if version:
            mediciones = list(version.mediciones.all())
            if anio and anio.isdigit():
                mediciones = [m for m in mediciones if m.periodo.anio == int(anio)]
        ultima = ultima_medicion_publicada(self.object)
        metas = list(version.metas.all()) if version else []
        meta = meta_para(version, ultima) if ultima else (metas[0] if metas else None)
        ctx.update(
            {
                "version": version,
                "mediciones": mediciones,
                "ultima": ultima,
                "semaforo": semaforo(version, ultima.valor_calculado, meta) if ultima else "gris",
                "meta": meta,
                "puede_cargar": puede_cargar_area(self.request.user, self.object.area),
                "anio": anio or "",
                "anios": sorted({m.periodo.anio for m in (version.mediciones.all() if version else [])}, reverse=True),
                "chart_id": "evolucion",
                "unidad": version.unidad_resultado if version else "",
                "nd_ultima": texto_nd(ultima, version) if ultima and version else "N s/d · D s/d",
                "filas_nd": [
                    {"medicion": m, "nd": texto_nd(m, version)} for m in mediciones
                ] if version else [],
                "chart": json.dumps(serie_desde_mediciones(version, mediciones) if version else {"labels": [], "values": [], "colors": [], "detalles": []}),
            }
        )
        if self.request.headers.get("HX-Request"):
            self.template_name = "tablero/_chart.html"
        return ctx


class CargarMedicionView(AreaPermisoMixin, FormView):
    template_name = "tablero/cargar.html"
    form_class = MedicionForm

    def area_objeto(self):
        self.indicador = get_object_or_404(
            Indicador.objects.select_related("area"),
            pk=self.kwargs["pk"],
        )
        return self.indicador.area

    def dispatch(self, request, *args, **kwargs):
        self.indicador = get_object_or_404(Indicador, pk=kwargs["pk"])
        if not puede_cargar_area(request.user, self.indicador.area):
            raise Http404()
        self.version = self.indicador.version_vigente()
        if not self.version:
            raise Http404()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["version"] = self.version
        periodo_id = self.request.GET.get("periodo") or self.request.POST.get("periodo")
        if periodo_id:
            existente = Medicion.objects.filter(
                indicador_version=self.version, periodo_id=periodo_id
            ).first()
            if existente:
                kwargs["instance"] = existente
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["indicador"] = self.indicador
        ctx["version"] = self.version
        return ctx

    def form_valid(self, form):
        medicion = form.save(commit=False)
        medicion.indicador_version = self.version
        medicion.usuario_carga = self.request.user
        if not medicion.fecha_corte:
            medicion.fecha_corte = medicion.periodo.fecha_fin
        existente = Medicion.objects.filter(
            indicador_version=self.version, periodo=medicion.periodo
        ).first()
        if existente and existente.pk != getattr(medicion, "pk", None):
            existente.numerador_valor = medicion.numerador_valor
            existente.denominador_valor = medicion.denominador_valor
            existente.conclusion = medicion.conclusion
            existente.es_prueba = medicion.es_prueba
            existente.estado = medicion.estado
            existente.usuario_carga = self.request.user
            existente.fecha_corte = medicion.periodo.fecha_fin
            existente.save()
        else:
            medicion.save()
        messages.success(self.request, "Medición guardada.")
        return redirect("tablero:ficha", pk=self.indicador.pk)

    def get_success_url(self):
        return reverse("tablero:ficha", args=[self.indicador.pk])
