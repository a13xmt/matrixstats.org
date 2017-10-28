from django.core.management.base import BaseCommand, CommandError
from room_stats.utils import update_server_stats

class Command(BaseCommand):
    help = 'Update matrix server statistics'

    def handle(self, *args, **options):
        update_server_stats()
