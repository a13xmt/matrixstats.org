# Generated by Django 2.0.1 on 2018-04-20 09:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('room_stats', '0030_server_sync_allowed'),
    ]

    operations = [
        migrations.AddField(
            model_name='server',
            name='last_sync_time',
            field=models.DateTimeField(blank=True, default=None, null=True),
        ),
    ]
