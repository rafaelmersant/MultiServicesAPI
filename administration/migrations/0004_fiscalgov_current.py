# Generated by Django 2.2.4 on 2019-08-30 08:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0003_auto_20190829_1750'),
    ]

    operations = [
        migrations.AddField(
            model_name='fiscalgov',
            name='current',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
