# Generated by Django 4.0.3 on 2022-03-28 23:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0031_remove_productsstock_id_product_ocurrences_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productsstock',
            name='product',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='stocks', to='products.product'),
        ),
    ]