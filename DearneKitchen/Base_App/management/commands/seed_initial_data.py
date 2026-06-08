from django.core.management import call_command
from django.core.management.base import BaseCommand

from Base_App.models import ItemList


class Command(BaseCommand):
    help = 'Load initial menu/review data if the database is empty.'

    def handle(self, *args, **options):
        if ItemList.objects.exists():
            self.stdout.write(self.style.WARNING('Database already has data; skipping seed.'))
            return

        call_command('loaddata', 'initial_data')
        self.stdout.write(self.style.SUCCESS('Initial data loaded successfully.'))
