# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-06-18 06:42
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='File',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.TextField()),
                ('filepath_hash', models.TextField()),
                ('last_modified', models.DateTimeField()),
                ('added_at', models.DateTimeField()),
            ],
        ),
        migrations.CreateModel(
            name='Path',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('source', models.TextField()),
                ('destination', models.TextField()),
                ('accepted', models.BooleanField(default=True)),
                ('added_at', models.DateTimeField()),
                ('filename', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='filename_path', to='data.File')),
            ],
        ),
    ]