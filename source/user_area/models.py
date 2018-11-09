from django.db import models
from django.conf import settings
from uuid import uuid4
from hashid_field import HashidAutoField

from room_stats.models import Server

def upload_to(instance, filename):
    ext = filename.split('.')[-1]
    fname = "%s.%s" % (str(uuid4()), ext)
    return 'servers/%s' % (fname)

class BoundServer(models.Model):
    SERVER_LOAD_CHOICES = (
        ('l', 'Low'),
        ('m', 'Medium'),
        ('h', 'High'),
        ('f', 'Full')
    )
    PAYMENT_MODEL_CHOICES = (
        ('f', 'Free'),
        ('p', 'Paid')
    )
    REGISTRATION_CHOICES = (
        ('o', 'Open'),
        ('r', 'Open (on-request)'),
        ('c', 'Closed'),
        ('t', 'Closed (temporarily)')
    )
    MATURITY_CHOICES = (
        ('s', 'Stable'),
        ('e', 'Experimental'),
    )

    id = HashidAutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    server = models.ForeignKey(Server, on_delete=models.SET_NULL, null=True)
    is_verified = models.BooleanField(default=False)
    last_verified_at = models.DateTimeField(blank=True, null=True)
    verification_code = models.UUIDField(default=uuid4)

    header = models.CharField(max_length=64, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(upload_to=upload_to, blank=True, null=True)
    rules = models.TextField(blank=True, null=True)
    maturity = models.CharField(max_length=1, choices=MATURITY_CHOICES, default='s')
    server_load = models.CharField(max_length=1, choices=SERVER_LOAD_CHOICES, default='l')
    payment_model = models.CharField(max_length=1, choices=PAYMENT_MODEL_CHOICES, default='f')
    registration = models.CharField(max_length=1, choices=REGISTRATION_CHOICES, default='o')

    def get_logo_url(self):
        return '/static/%s' % (self.logo.name if self.logo else 'img/no-logo.png')

    def get_hostname(self):
        return self.server.hostname if self.server else "-"

    def __str__(self):
        return self.server.hostname if self.server else "-"

    def __repr__(self):
        return self.server.hostname if self.server else "-"

