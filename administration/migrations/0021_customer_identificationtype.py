# Generated by Django 2.2.4 on 2019-11-30 02:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0020_customer_identification'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='identificationType',
            field=models.CharField(blank=True, max_length=1),
        ),
    ]
