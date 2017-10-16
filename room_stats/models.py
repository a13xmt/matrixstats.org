from django.db import models

class Room(models.Model):
    id = models.CharField(max_length=511, primary_key=True)
    name = models.TextField(blank=True, null=True)
    aliases = models.TextField(blank=True, null=True)
    topic = models.TextField(blank=True, null=True)
    members_count = models.IntegerField()
    avatar_url = models.TextField(blank=True, null=True)
    is_public_readable = models.BooleanField()
    is_guest_writeable = models.BooleanField()
