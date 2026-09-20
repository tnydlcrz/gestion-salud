from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q


class Frecuencia(models.TextChoices):
    MENSUAL = "mensual", "Mensual"
    TRIMESTRAL = "trimestral", "Trimestral"
    CUATRIMESTRAL = "cuatrimestral", "Cuatrimestral"
    SEMESTRAL = "semestral", "Semestral"
    ANUAL = "anual", "Anual"


class AreaDireccion(models.Model):
    nombre = models.CharField(max_length=200, unique=True)

    class Meta:
        verbose_name = "área / dirección"
        verbose_name_plural = "áreas / direcciones"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Dimension(models.Model):
    nombre = models.CharField(max_length=200, unique=True)

    class Meta:
        verbose_name = "dimensión"
        verbose_name_plural = "dimensiones"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Responsable(models.Model):
    nombre = models.CharField(max_length=200)
    area = models.ForeignKey(AreaDireccion, on_delete=models.CASCADE, related_name="responsables")
    correo = models.EmailField(blank=True)
    telefono = models.CharField(max_length=50, blank=True)

    class Meta:
        verbose_name = "responsable"
        verbose_name_plural = "responsables"

    def __str__(self):
        return f"{self.nombre} ({self.area})"


class Periodo(models.Model):
    anio = models.PositiveIntegerField()
    frecuencia = models.CharField(max_length=20, choices=Frecuencia.choices)
    nro_periodo = models.PositiveSmallIntegerField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    label = models.CharField(max_length=80)

    class Meta:
        verbose_name = "período"
        verbose_name_plural = "períodos"
        ordering = ["fecha_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["anio", "frecuencia", "nro_periodo"],
                name="periodo_unico",
            ),
        ]

    def __str__(self):
        return self.label


class Indicador(models.Model):
    nombre = models.CharField(max_length=300)
    area = models.ForeignKey(AreaDireccion, on_delete=models.CASCADE, related_name="indicadores")
    area_direccion = models.CharField(
        max_length=200,
        blank=True,
        help_text="Área/Dirección del cuadro de indicadores, si difiere del área de acceso.",
    )
    dimension = models.ForeignKey(Dimension, on_delete=models.PROTECT, related_name="indicadores")
    responsable = models.ForeignKey(
        Responsable, on_delete=models.SET_NULL, null=True, blank=True, related_name="indicadores"
    )
    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="indicadores_creados",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="indicadores_actualizados",
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "indicador"
        verbose_name_plural = "indicadores"
        ordering = ["area__nombre", "nombre"]

    def __str__(self):
        return self.nombre

    @property
    def etiqueta_area_direccion(self):
        return self.area_direccion or (self.area.nombre if self.area_id else "")

    def version_vigente(self):
        return self.versiones.filter(fecha_vigencia_hasta__isnull=True).first()


class IndicadorVersion(models.Model):
    class TipoCalculo(models.TextChoices):
        VALOR_DIRECTO = "valor_directo", "Valor directo"
        RAZON = "razon", "Razón (num / den)"

    class MetaTipo(models.TextChoices):
        MINIMO = "minimo", "Mínimo"
        MAXIMO = "maximo", "Máximo"
        RANGO = "rango", "Rango"
        SOSTENER = "sostener", "Sostener"
        SEGUIMIENTO = "seguimiento", "Seguimiento"

    class Sentido(models.TextChoices):
        ASCENDENTE = "ascendente", "Ascendente (más es mejor)"
        DESCENDENTE = "descendente", "Descendente (menos es mejor)"

    indicador = models.ForeignKey(Indicador, on_delete=models.CASCADE, related_name="versiones")
    version_num = models.PositiveIntegerField()
    fecha_vigencia_desde = models.DateField()
    fecha_vigencia_hasta = models.DateField(null=True, blank=True)
    formula_calculo = models.TextField()
    tipo_calculo = models.CharField(max_length=20, choices=TipoCalculo.choices)
    numerador_descripcion = models.CharField(max_length=300, blank=True)
    numerador_unidad = models.CharField(max_length=80, blank=True)
    denominador_descripcion = models.CharField(max_length=300, blank=True)
    denominador_unidad = models.CharField(max_length=80, blank=True)
    unidad_resultado = models.CharField(max_length=40, blank=True)
    meta_tipo = models.CharField(max_length=20, choices=MetaTipo.choices)
    sentido_mejora = models.CharField(max_length=20, choices=Sentido.choices)
    fuente_datos = models.CharField(max_length=300, blank=True)
    frecuencia = models.CharField(max_length=20, choices=Frecuencia.choices)
    objetivo_operativo = models.TextField(blank=True)
    nota_metodologica = models.TextField(blank=True)

    class Meta:
        verbose_name = "versión de indicador"
        verbose_name_plural = "versiones de indicador"
        ordering = ["indicador", "-version_num"]
        constraints = [
            models.UniqueConstraint(
                fields=["indicador", "version_num"],
                name="indicador_version_num_unico",
            ),
            models.UniqueConstraint(
                fields=["indicador"],
                condition=Q(fecha_vigencia_hasta__isnull=True),
                name="una_version_vigente_por_indicador",
            ),
        ]

    def __str__(self):
        return f"{self.indicador} v{self.version_num}"

    @classmethod
    def crear_nueva(cls, indicador, fecha_desde, **kwargs):
        with transaction.atomic():
            vigente = indicador.version_vigente()
            version_num = 1
            if vigente:
                vigente.fecha_vigencia_hasta = fecha_desde
                vigente.save(update_fields=["fecha_vigencia_hasta"])
                version_num = vigente.version_num + 1
            return cls.objects.create(
                indicador=indicador,
                version_num=version_num,
                fecha_vigencia_desde=fecha_desde,
                **kwargs,
            )


class MetaPeriodo(models.Model):
    indicador_version = models.ForeignKey(
        IndicadorVersion, on_delete=models.CASCADE, related_name="metas"
    )
    meta_min = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    meta_max = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    fecha_inicio_meta = models.DateField()
    fecha_fin_meta = models.DateField()

    class Meta:
        verbose_name = "meta de período"
        verbose_name_plural = "metas de período"
        ordering = ["fecha_inicio_meta"]

    def __str__(self):
        return f"Meta {self.indicador_version} {self.fecha_inicio_meta}–{self.fecha_fin_meta}"

    def clean(self):
        qs = MetaPeriodo.objects.filter(indicador_version=self.indicador_version).exclude(pk=self.pk)
        if qs.filter(
            fecha_inicio_meta__lte=self.fecha_fin_meta,
            fecha_fin_meta__gte=self.fecha_inicio_meta,
        ).exists():
            raise ValidationError("La meta se solapa con otra de la misma versión.")


class Medicion(models.Model):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        PUBLICADO = "publicado", "Publicado"

    indicador_version = models.ForeignKey(
        IndicadorVersion, on_delete=models.CASCADE, related_name="mediciones"
    )
    periodo = models.ForeignKey(Periodo, on_delete=models.PROTECT, related_name="mediciones")
    fecha_corte = models.DateField()
    numerador_valor = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    denominador_valor = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    valor_calculado = models.DecimalField(max_digits=16, decimal_places=4, null=True, blank=True)
    es_prueba = models.BooleanField(
        default=False,
        help_text="Dato de prueba o provisorio (se muestra como VP).",
    )
    conclusion = models.TextField(blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PUBLICADO)
    usuario_carga = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="mediciones_cargadas",
    )
    fecha_carga = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "medición"
        verbose_name_plural = "mediciones"
        ordering = ["periodo__fecha_inicio"]
        constraints = [
            models.UniqueConstraint(
                fields=["indicador_version", "periodo"],
                name="medicion_unica_por_periodo",
            ),
        ]

    def __str__(self):
        return f"{self.indicador_version.indicador} · {self.periodo}"

    def calcular_valor(self):
        from .services import calcular_valor

        self.valor_calculado = calcular_valor(
            self.indicador_version,
            self.numerador_valor,
            self.denominador_valor,
        )

    def save(self, *args, **kwargs):
        if self.fecha_corte is None and self.periodo_id:
            self.fecha_corte = self.periodo.fecha_fin
        self.calcular_valor()
        super().save(*args, **kwargs)

    def meta_aplicable(self):
        corte = self.fecha_corte
        candidatas = [
            meta
            for meta in self.indicador_version.metas.all()
            if meta.fecha_inicio_meta <= corte <= meta.fecha_fin_meta
        ]
        if not candidatas:
            return None
        return max(candidatas, key=lambda meta: meta.fecha_inicio_meta)

    def semaforo(self):
        from .services import semaforo

        return semaforo(self.indicador_version, self.valor_calculado, self.meta_aplicable())
