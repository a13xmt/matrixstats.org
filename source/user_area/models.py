from django.db import models
from django.conf import settings
from uuid import uuid4
from hashid_field import HashidAutoField

from room_stats.models import Server


class BoundServer(models.Model):
    id = HashidAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    server = models.ForeignKey(Server, on_delete=models.SET_NULL, null=True)

    is_verified = models.BooleanField(default=False)
    last_verified_at = models.DateTimeField(blank=True, null=True)
    verification_code = models.UUIDField(default=uuid4)

    def __str__(self):
        return self.server.hostname

    def __repr__(self):
        return self.server.hostname

