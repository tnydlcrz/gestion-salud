from decimal import Decimal, InvalidOperation

from django import forms

from .models import Medicion, Periodo


class CantidadInput(forms.TextInput):
    """Evita el spinner de HTML5, cuyo paso sigue los 4 decimales del DecimalField."""

    def __init__(self, attrs=None):
        extra = {"inputmode": "decimal", "autocomplete": "off"}
        if attrs:
            extra.update(attrs)
        super().__init__(attrs=extra)

    def format_value(self, value):
        if value is None or value == "":
            return ""
        try:
            numero = Decimal(str(value))
        except (InvalidOperation, TypeError):
            return super().format_value(value)
        if numero == numero.to_integral_value():
            return str(int(numero))
        return format(numero.normalize(), "f")


class MedicionForm(forms.ModelForm):
    class Meta:
        model = Medicion
        fields = [
            "periodo",
            "numerador_valor",
            "denominador_valor",
            "conclusion",
            "es_prueba",
            "estado",
        ]
        widgets = {
            "numerador_valor": CantidadInput(),
            "denominador_valor": CantidadInput(),
            "conclusion": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, version=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.version = version
        frecuencia = version.frecuencia if version else None
        self.fields["periodo"].queryset = Periodo.objects.filter(frecuencia=frecuencia).order_by(
            "-fecha_inicio"
        )
        self.fields["periodo"].label = "Período"
        self.fields["numerador_valor"].label = version.numerador_descripcion or "Valor"
        self.fields["numerador_valor"].localize = True
        self.fields["denominador_valor"].label = version.denominador_descripcion or "Denominador"
        self.fields["denominador_valor"].localize = True
        self.fields["conclusion"].label = "Conclusión del período"
        self.fields["es_prueba"].label = "Valor de prueba (VP)"
        self.fields["es_prueba"].help_text = "Marcar si el numerador/denominador aún no es el dato real."
        if version and version.tipo_calculo == version.TipoCalculo.VALOR_DIRECTO:
            self.fields["denominador_valor"].required = False
            self.fields["denominador_valor"].widget = forms.HiddenInput()
            self.fields["numerador_valor"].help_text = "Unidades absolutas (enteros o decimales, según el indicador)."
        else:
            self.fields["numerador_valor"].help_text = "Cantidad del numerador."
            self.fields["denominador_valor"].help_text = "Cantidad del denominador."
        for field in self.fields.values():
            css = "input-field"
            if isinstance(field.widget, forms.Textarea):
                css = "input-field min-h-[6rem]"
            field.widget.attrs.setdefault("class", css)

    def clean(self):
        cleaned = super().clean()
        version = self.version
        if version and version.tipo_calculo == version.TipoCalculo.RAZON:
            if cleaned.get("denominador_valor") in (None, ""):
                self.add_error("denominador_valor", "Requerido para una razón.")
            elif cleaned.get("denominador_valor") == 0:
                self.add_error("denominador_valor", "El denominador no puede ser cero.")
        return cleaned
