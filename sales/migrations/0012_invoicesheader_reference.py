# Generated by Django 2.2.4 on 2019-10-05 00:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0011_invoicesheader_paid'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoicesheader',
            name='reference',
            field=models.CharField(blank=True, max_length=50),
        ),
    ]
