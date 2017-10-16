from django.contrib import admin

from room_stats.models import Room

class RoomAdmin(admin.ModelAdmin):
    list_display = ('members_count', 'name', 'topic', 'is_public_readable', 'is_guest_writeable')
    ordering = ('-members_count', )

admin.site.register(Room, RoomAdmin)
