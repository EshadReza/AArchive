from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.utils import timezone

from apps.access.services import lock_privilege_changes
from apps.accounts.models import LoginAttempt, User
from apps.audit.services import AuditContext, record_event

from .throttle import consume_attempt, identity_key


def sign_in(request, *, email, password):
    email = User.objects.normalize_email(email)
    retry = consume_attempt(email, request.META.get("REMOTE_ADDR", "unknown"))
    if retry:
        return None, retry
    authenticated = authenticate(request, email=email, password=password)
    with transaction.atomic():
        # Hashing happens outside this low-volume privilege lock. Recheck password
        # revision and eligibility after acquiring it, before creating the session.
        lock_privilege_changes()
        user = (
            User.objects.select_for_update().filter(pk=authenticated.pk).first()
            if authenticated
            else None
        )
        if user is None or not user.is_login_eligible or user.password != authenticated.password:
            record_event(
                system_actor="authentication",
                action="auth.login.failed",
                target_id="system",
                new_value={"outcome": "invalid_credentials"},
            )
            return None, None
        if user.state == "INACTIVE":
            user.state = "ACTIVE"
            user.save(update_fields=["state", "updated_at"])
            record_event(
                actor=user,
                action="accounts.state.changed",
                target_id=user.pk,
                previous_value={"state": "INACTIVE"},
                new_value={"state": "ACTIVE"},
            )
        login(request, user, backend="apps.accounts.auth.backend.PlatformBackend")
        request.session.set_expiry(timezone.now() + timedelta(seconds=settings.SESSION_COOKIE_AGE))
        request.session.save()
        record_event(
            actor=user,
            action="auth.login.succeeded",
            target_id=user.pk,
            new_value={"outcome": "succeeded"},
            context=AuditContext(channel="browser"),
        )
        LoginAttempt.objects.filter(pk=identity_key(email)).update(attempts=0)
    return user, None


@transaction.atomic
def sign_out(request):
    user = request.user
    if user is not None and user.is_authenticated:
        record_event(
            actor=user,
            action="auth.session.ended",
            target_id=user.pk,
            new_value={"outcome": "logout"},
            context=AuditContext(channel="browser"),
        )
    logout(request)
