from datetime import timedelta
from ipaddress import ip_address
from math import ceil

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from apps.accounts.models import LoginAttempt


@transaction.atomic
def consume_attempt(email, peer):
    """Registration/resend share budgets; verification uses the same peer budget."""
    try:
        peer = str(ip_address(peer))
    except ValueError:
        peer = "unknown"
    buckets = [("peer", peer, settings.REGISTRATION_IP_LIMIT)]
    if email is not None:
        buckets.append(("email", email, settings.REGISTRATION_EMAIL_LIMIT))
    now = timezone.now()
    rows = []
    for kind, value, limit in buckets:
        key = salted_hmac(f"registration.{kind}", value, algorithm="sha256").hexdigest()
        LoginAttempt.objects.get_or_create(
            key=key,
            defaults={"resets_at": now + timedelta(seconds=settings.REGISTRATION_WINDOW_SECONDS)},
        )
        row = LoginAttempt.objects.select_for_update().get(pk=key)
        if row.resets_at <= now:
            row.attempts = 0
            row.resets_at = now + timedelta(seconds=settings.REGISTRATION_WINDOW_SECONDS)
        if row.attempts >= limit:
            return max(1, ceil((row.resets_at - now).total_seconds()))
        rows.append(row)
    for row in rows:
        row.attempts += 1
        row.save(update_fields=["attempts", "resets_at"])
    return None
