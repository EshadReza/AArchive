from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.access.services import bootstrap_administrator
from apps.accounts.models import User


class Command(BaseCommand):
    help = "Assign the first Administrator to an existing verified/approved eligible account."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)

    def handle(self, *args, **options):
        try:
            user = User.objects.get_by_natural_key(options["email"])
            bootstrap_administrator(subject_id=user.pk)
        except (User.DoesNotExist, PermissionDenied, ValidationError) as exc:
            raise CommandError(
                "Bootstrap refused: account missing/ineligible or an admin exists."
            ) from exc
        self.stdout.write(self.style.SUCCESS("First Administrator assigned and audited."))
