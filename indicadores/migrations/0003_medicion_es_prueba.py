from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("indicadores", "0002_indicador_area_direccion"),
    ]

    operations = [
        migrations.AddField(
            model_name="medicion",
            name="es_prueba",
            field=models.BooleanField(
                default=False,
                help_text="Dato de prueba o provisorio (se muestra como VP).",
            ),
        ),
    ]
