from datetime import timedelta
from ipaddress import ip_address
from math import ceil

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from apps.accounts.models import LoginAttempt
from apps.audit.services import record_event


def identity_key(email):
    return salted_hmac("login.identity", email, algorithm="sha256").hexdigest()


@transaction.atomic
def consume_attempt(email, peer):
    try:
        peer = str(ip_address(peer))
    except ValueError:
        peer = "unknown"
    buckets = [
        (salted_hmac("login.peer", peer, algorithm="sha256").hexdigest(), settings.LOGIN_IP_LIMIT),
        (identity_key(email), settings.LOGIN_ATTEMPT_LIMIT),
    ]
    now = timezone.now()
    reset = now + timedelta(seconds=settings.LOGIN_WINDOW_SECONDS)
    rows = []
    # Always lock peer before identity. Reject a blocked peer before allocating
    # another identifier row, so varied emails cannot grow storage past its budget.
    for key, limit in buckets:
        LoginAttempt.objects.get_or_create(key=key, defaults={"resets_at": reset})
        row = LoginAttempt.objects.select_for_update().get(pk=key)
        if row.resets_at <= now:
            row.attempts, row.resets_at = 0, reset
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
            action="auth.login.locked",
            target_id="system",
            new_value={"outcome": "temporary_lockout"},
        )
    return None
