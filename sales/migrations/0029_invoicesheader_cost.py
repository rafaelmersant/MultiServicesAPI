# Generated by Django 4.0.3 on 2022-05-31 18:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0028_alter_invoicesheader_paymentmethod'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoicesheader',
            name='cost',
            field=models.DecimalField(decimal_places=6, default=0, max_digits=18),
        ),
    ]
