# Generated by Django 2.2.4 on 2019-09-28 16:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0006_auto_20190927_1323'),
    ]

    operations = [
        migrations.RenameField(
            model_name='user',
            old_name='fullName',
            new_name='name',
        ),
        migrations.RemoveField(
            model_name='user',
            name='userName',
        ),
    ]
