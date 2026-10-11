from datetime import timedelta
from ipaddress import ip_address
from math import ceil

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from apps.accounts.models import LoginAttempt
from apps.audit.services import record_event


@transaction.atomic
def consume_attempt(identity, peer):
    try:
        peer = str(ip_address(peer))
    except ValueError:
        peer = "unknown"
    buckets = [("peer", peer, settings.RECOVERY_IP_LIMIT)]
    if identity is not None:
        buckets.append(("identity", identity, settings.RECOVERY_IDENTITY_LIMIT))
    now = timezone.now()
    rows = []
    for kind, value, limit in buckets:
        key = salted_hmac(f"recovery.{kind}", value, algorithm="sha256").hexdigest()
        LoginAttempt.objects.get_or_create(
            key=key,
            defaults={"resets_at": now + timedelta(seconds=settings.RECOVERY_WINDOW_SECONDS)},
        )
        row = LoginAttempt.objects.select_for_update().get(pk=key)
        if row.resets_at <= now:
            row.attempts = 0
            row.resets_at = now + timedelta(seconds=settings.RECOVERY_WINDOW_SECONDS)
        if row.attempts >= limit:
            return max(1, ceil((row.resets_at - now).total_seconds()))
        rows.append((row, limit))
    reached = False
    for row, limit in rows:
        row.attempts += 1
        row.save(update_fields=["attempts", "resets_at"])
        reached |= row.attempts == limit
    if reached:
        record_event(
            system_actor="authentication",
            action="auth.recovery.limited",
            target_id="system",
            new_value={"outcome": "temporary_lockout"},
        )
    return None
