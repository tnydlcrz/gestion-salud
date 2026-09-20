from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario, UsuarioArea


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("email", "nombre", "es_admin_global", "is_active")
    list_filter = ("es_admin_global", "is_active", "is_staff")
    search_fields = ("email", "nombre")
    ordering = ("email",)
    fieldsets = UserAdmin.fieldsets + (
        ("Tablero", {"fields": ("nombre", "es_admin_global")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("email", "nombre", "es_admin_global")}),
    )


@admin.register(UsuarioArea)
class UsuarioAreaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "area", "rol", "fecha_alta", "fecha_baja")
    list_filter = ("rol", "area")
    search_fields = ("usuario__email", "usuario__nombre", "area__nombre")
