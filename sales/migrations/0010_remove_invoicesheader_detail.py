# Generated by Django 2.2.4 on 2019-10-04 17:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sales', '0009_invoicesheader_detail'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='invoicesheader',
            name='detail',
        ),
    ]
