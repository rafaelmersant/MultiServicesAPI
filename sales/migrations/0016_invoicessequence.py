# Generated by Django 2.2.4 on 2019-10-22 12:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('administration', '0017_auto_20191014_0131'),
        ('sales', '0015_invoicesdetail_quantity'),
    ]

    operations = [
        migrations.CreateModel(
            name='InvoicesSequence',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sequence', models.IntegerField()),
                ('creationDate', models.DateTimeField(auto_now_add=True)),
                ('createdUser', models.EmailField(blank=True, max_length=254, null=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='administration.Company')),
            ],
        ),
    ]
