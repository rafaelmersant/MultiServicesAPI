# Generated by Django 2.2.4 on 2020-04-01 19:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0027_auto_20200314_1830'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productsstock',
            name='product',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='products.Product', unique=True),
        ),
    ]