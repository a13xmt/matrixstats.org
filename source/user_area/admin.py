from django.contrib import admin
from .models import BoundServer

class BoundServerAdmin(admin.ModelAdmin):
    list_display = ('user', 'server', 'is_verified', 'last_verified_at')


admin.site.register(BoundServer, BoundServerAdmin)
