from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from room_stats.models import PromotionRequest

class Command(BaseCommand):
    help = 'Delete expired room promotions'

    def handle(self, *args, **options):
        PromotionRequest.objects.filter(remove_at__lte=datetime.now()).delete()

