# Generated by Django 2.2.4 on 2019-12-19 22:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0021_auto_20191127_0816'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='cost',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='itbis',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='product',
            name='price',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='productsstock',
            name='quantityAvailable',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='productsstock',
            name='quantityHold',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='productstracking',
            name='cost',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='productstracking',
            name='itbis',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='productstracking',
            name='price',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='productstracking',
            name='quantity',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='productstrackingheader',
            name='itbis',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=18, null=True),
        ),
        migrations.AlterField(
            model_name='productstrackingheader',
            name='totalAmount',
            field=models.DecimalField(decimal_places=6, max_digits=18, null=True),
        ),
    ]
