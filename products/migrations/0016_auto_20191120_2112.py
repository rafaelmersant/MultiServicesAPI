# Generated by Django 2.2.4 on 2019-11-21 02:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0019_auto_20191120_2112'),
        ('products', '0015_auto_20191026_1509'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='productstracking',
            name='provider',
        ),
        migrations.AddField(
            model_name='productstracking',
            name='itbis',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True),
        ),
        migrations.CreateModel(
            name='ProductsTrackingHeader',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('docDate', models.DateTimeField(blank=True)),
                ('ncf', models.CharField(blank=True, max_length=13, null=True)),
                ('totalAmount', models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ('itbis', models.DecimalField(blank=True, decimal_places=2, max_digits=18, null=True)),
                ('creationDate', models.DateTimeField(blank=True)),
                ('serverDate', models.DateTimeField(auto_now_add=True)),
                ('createdUser', models.EmailField(blank=True, max_length=254, null=True)),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='administration.Provider')),
            ],
        ),
    ]