from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("indicadores", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="indicador",
            name="area_direccion",
            field=models.CharField(
                blank=True,
                help_text="Área/Dirección del cuadro de indicadores, si difiere del área de acceso.",
                max_length=200,
            ),
        ),
    ]
