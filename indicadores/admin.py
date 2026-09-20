from django.contrib import admin

from .models import (
    AreaDireccion,
    Dimension,
    Indicador,
    IndicadorVersion,
    Medicion,
    MetaPeriodo,
    Periodo,
    Responsable,
)


@admin.register(AreaDireccion)
class AreaAdmin(admin.ModelAdmin):
    search_fields = ("nombre",)


@admin.register(Dimension)
class DimensionAdmin(admin.ModelAdmin):
    search_fields = ("nombre",)


@admin.register(Responsable)
class ResponsableAdmin(admin.ModelAdmin):
    list_display = ("nombre", "area", "correo")
    list_filter = ("area",)


@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ("label", "frecuencia", "anio", "fecha_inicio", "fecha_fin")
    list_filter = ("frecuencia", "anio")


class MetaInline(admin.TabularInline):
    model = MetaPeriodo
    extra = 0


class VersionInline(admin.StackedInline):
    model = IndicadorVersion
    extra = 0


@admin.register(Indicador)
class IndicadorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "area", "area_direccion", "dimension", "activo")
    list_filter = ("area", "dimension", "activo")
    search_fields = ("nombre", "area_direccion")
    inlines = [VersionInline]


@admin.register(IndicadorVersion)
class VersionAdmin(admin.ModelAdmin):
    list_display = ("indicador", "version_num", "frecuencia", "meta_tipo", "fecha_vigencia_hasta")
    list_filter = ("frecuencia", "meta_tipo")
    inlines = [MetaInline]


@admin.register(Medicion)
class MedicionAdmin(admin.ModelAdmin):
    list_display = ("indicador_version", "periodo", "valor_calculado", "es_prueba", "estado")
    list_filter = ("estado", "es_prueba", "periodo__frecuencia")
