from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import LoginAttempt


class Command(BaseCommand):
    help = "Remove expired login attempt counters; current lockouts are retained."

    def handle(self, *args, **options):
        count, _ = LoginAttempt.objects.filter(resets_at__lte=timezone.now()).delete()
        self.stdout.write(f"Removed {count} expired login counters.")
