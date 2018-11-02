from django.db import models
from django.conf import settings
from room_stats.models import Server

class Account(models.Model):
    STATUS_CHOICES = (
        ('p', "Processing"),
        ('i', "Invited"),
        ('r', "Registered"),
        ('e', "Registration Error")
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='p')
    registration_code = models.CharField(max_length=36, default='', editable=False)
    validation_code = models.CharField(max_length=36, default='', editable=False)

    def __str__(self):
        return self.user.username


class BoundServer(models.Model):
    pass
    # account = models.ForeignKey(Account, on_delete=models.CASCADE)
    # homeserver = models.ForeignKey(Server, on_delete=models.CASCADE)

    # dns_validation_code = models.CharField(max_length=255)
