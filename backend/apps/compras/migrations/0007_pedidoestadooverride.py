from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("compras", "0006_alter_pedidos_estado_devolucion_devolucionitem"),
    ]

    operations = [
        migrations.CreateModel(
            name="PedidoEstadoOverride",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("estado_anterior", models.CharField(max_length=20)),
                ("estado_nuevo", models.CharField(max_length=20)),
                ("motivo", models.TextField()),
                ("fecha", models.DateTimeField(auto_now_add=True)),
                (
                    "pedido",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="overrides",
                        to="compras.pedidos",
                    ),
                ),
                (
                    "staff",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pedido_overrides",
                        to="usuarios.usuario",
                    ),
                ),
            ],
        ),
    ]
