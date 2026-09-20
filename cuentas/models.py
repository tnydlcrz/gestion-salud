from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    nombre = models.CharField(max_length=200)
    email = models.EmailField("correo", unique=True)
    es_admin_global = models.BooleanField(
        default=False,
        help_text="Ve y administra todas las áreas.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "nombre"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"

    def __str__(self):
        return self.nombre or self.email

    @property
    def es_admin(self):
        return self.es_admin_global or self.is_superuser


class UsuarioArea(models.Model):
    class Rol(models.TextChoices):
        AREA = "area", "Área"
        COORDINADOR = "coordinador", "Coordinador"

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="membresias",
    )
    area = models.ForeignKey(
        "indicadores.AreaDireccion",
        on_delete=models.CASCADE,
        related_name="membresias",
    )
    rol = models.CharField(max_length=20, choices=Rol.choices)
    otorgado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="membresias_otorgadas",
    )
    fecha_alta = models.DateTimeField(auto_now_add=True)
    fecha_baja = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "asignación de área"
        verbose_name_plural = "asignaciones de área"
        indexes = [
            models.Index(fields=["usuario", "fecha_baja"]),
        ]

    def __str__(self):
        estado = "vigente" if self.fecha_baja is None else "cerrada"
        return f"{self.usuario} · {self.area} ({self.rol}, {estado})"

    @property
    def vigente(self):
        return self.fecha_baja is None
