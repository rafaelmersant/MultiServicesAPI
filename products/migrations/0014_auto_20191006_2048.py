# Generated by Django 2.2.4 on 2019-10-07 00:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0013_productstracking_concept'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='cost',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='itbis',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='productsstock',
            name='quantityAvailable',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='productsstock',
            name='quantityHold',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='productstracking',
            name='quantity',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
    ]
