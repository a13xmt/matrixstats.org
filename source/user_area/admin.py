from django.contrib import admin
from .models import BoundServer

def first_seen_at(object):
  return object.server.first_seen_at if object.server else None

def last_seen_at(object):
    return object.server.last_seen_at if object.server else None

class BoundServerAdmin(admin.ModelAdmin):
    list_display = ('user', '__str__', first_seen_at, last_seen_at, 'is_verified', 'last_verified_at')


admin.site.register(BoundServer, BoundServerAdmin)
