from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="demand_sku",
            field=models.PositiveSmallIntegerField(
                default=1, help_text="demand SKU id (1-50)"
            ),
        ),
    ]
