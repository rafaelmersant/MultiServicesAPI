# Generated by Django 2.2.4 on 2019-10-09 03:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0013_auto_20191008_2238'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fiscalgov',
            name='typeDoc',
            field=models.CharField(max_length=4),
        ),
    ]