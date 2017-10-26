from django.core.management.base import BaseCommand, CommandError
from room_stats.utils import update

class Command(BaseCommand):
    help = 'Update matrix rooms and store their statistics'

    def handle(self, *args, **options):
        update()
