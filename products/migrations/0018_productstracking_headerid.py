# Generated by Django 2.2.4 on 2019-11-21 03:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0017_productstrackingheader_company'),
    ]

    operations = [
        migrations.AddField(
            model_name='productstracking',
            name='headerId',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='products.ProductsTrackingHeader'),
        ),
    ]
