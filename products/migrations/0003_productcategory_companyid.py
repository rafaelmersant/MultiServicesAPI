# Generated by Django 2.2.4 on 2019-08-30 17:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0004_fiscalgov_current'),
        ('products', '0002_auto_20190830_1659'),
    ]

    operations = [
        migrations.AddField(
            model_name='productcategory',
            name='companyId',
            field=models.ForeignKey(default='', on_delete=django.db.models.deletion.CASCADE, to='administration.Company'),
            preserve_default=False,
        ),
    ]
