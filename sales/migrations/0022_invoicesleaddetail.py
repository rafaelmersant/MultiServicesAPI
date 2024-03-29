# Generated by Django 2.2.4 on 2021-02-16 00:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0029_auto_20210130_1223'),
        ('sales', '0021_invoicesheader_printed'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvoicesLeadDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.DecimalField(decimal_places=6, default=0, max_digits=18)),
                ('creationDate', models.DateTimeField(auto_now_add=True)),
                ('invoice', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='sales.InvoicesHeader')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='products.Product')),
            ],
        ),
    ]
