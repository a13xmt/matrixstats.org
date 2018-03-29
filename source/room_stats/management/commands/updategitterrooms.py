from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from room_stats.integrations.gitter import update_gitter_rooms

class Command(BaseCommand):
    help = 'Update descriptions and logos for all gitter rooms'

    def handle(self, *args, **options):
        update_gitter_rooms()
