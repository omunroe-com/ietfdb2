# -*- coding: utf-8 -*-
# Generated by Django 1.11.10 on 2018-02-25 12:07
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ipr', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='iprdisclosurebase',
            options={'ordering': ['-time', '-id']},
        ),
    ]
