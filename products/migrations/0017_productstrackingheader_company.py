# Generated by Django 2.2.4 on 2019-11-21 03:09

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0019_auto_20191120_2112'),
        ('products', '0016_auto_20191120_2112'),
    ]

    operations = [
        migrations.AddField(
            model_name='productstrackingheader',
            name='company',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='administration.Company'),
        ),
    ]