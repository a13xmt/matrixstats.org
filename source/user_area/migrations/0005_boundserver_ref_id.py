# Generated by Django 2.0.1 on 2018-11-05 11:58

from django.db import migrations
import hashid_field.field


class Migration(migrations.Migration):

    dependencies = [
        ('user_area', '0004_auto_20181105_1135'),
    ]

    operations = [
        migrations.AddField(
            model_name='boundserver',
            name='ref_id',
            field=hashid_field.field.HashidField(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890', default=0, min_length=7),
            preserve_default=False,
        ),
    ]
