# Generated by Django 2.2.4 on 2019-10-14 05:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0015_auto_20191014_0048'),
    ]

    operations = [
        migrations.AddField(
            model_name='fiscalgov',
            name='usedInInvoice',
            field=models.IntegerField(null=True),
        ),
    ]
