import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from apps.access.services import lock_privilege_changes
from apps.accounts.models import EmailVerification, PasswordReset, User
from apps.accounts.registration.services import account_digest, token_digest
from apps.audit.services import record_event

from .sessions import revoke_sessions

logger = logging.getLogger(__name__)


def deliver(email, token):
    link = f"{settings.PUBLIC_APP_ORIGIN}/reset-password#token={token}"
    try:
        count = send_mail(
            "Reset your AArchive password",
            "A password reset was requested for your AArchive account. Open this link to choose "
            f"a new password:\n{link}\n\n"
            f"The link expires in {settings.PASSWORD_RESET_SECONDS} seconds. "
            "If you did not request this, ignore this message. Your password has not changed.\n",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        if count != 1:
            logger.warning("Password reset mail was not delivered; request another link.")
    except Exception:
        logger.warning("Password reset mail was not delivered; request another link.")


@transaction.atomic
def request_reset(email):
    if not settings.PASSWORD_RESET_ENABLED:
        return
    lock_privilege_changes()
    user = (
        User.objects.select_for_update().filter(email=User.objects.normalize_email(email)).first()
    )
    if user is None or not user.is_login_eligible or not user.has_usable_password():
        return
    token = secrets.token_urlsafe(32)
    PasswordReset.objects.update_or_create(
        user=user,
        defaults={
            "token_digest": token_digest(token),
            "account_digest": account_digest(user),
            "expires_at": timezone.now() + timedelta(seconds=settings.PASSWORD_RESET_SECONDS),
            "consumed_at": None,
        },
    )
    record_event(
        system_actor="authentication",
        action="auth.reset.issued",
        target_id=user.pk,
        new_value={"outcome": "issued"},
    )
    transaction.on_commit(lambda: deliver(user.email, token))


def _set_password(user, password, *, actor=None):
    validate_password(password, user)
    if check_password(password, user.password):
        raise ValidationError("Choose a different password.")
    user.set_password(password)
    user.save(update_fields=["password", "updated_at"])
    PasswordReset.objects.filter(user=user, consumed_at__isnull=True).update(
        consumed_at=timezone.now()
    )
    EmailVerification.objects.filter(user=user).update(expires_at=timezone.now())
    revoke_sessions(user)
    record_event(
        actor=actor,
        system_actor="authentication" if actor is None else "",
        action="auth.password.changed",
        target_id=user.pk,
        new_value={"outcome": "reset" if actor is None else "changed"},
    )
    record_event(
        actor=actor,
        system_actor="authentication" if actor is None else "",
        action="auth.sessions.revoked",
        target_id=user.pk,
        new_value={"outcome": "password_change"},
    )


@transaction.atomic
def confirm_reset(token, password):
    if not settings.PASSWORD_RESET_ENABLED:
        return False
    lock_privilege_changes()
    digest = token_digest(token)
    challenge = PasswordReset.objects.filter(token_digest=digest).first()
    if challenge is None:
        return False
    user = User.objects.select_for_update().get(pk=challenge.user_id)
    challenge = PasswordReset.objects.select_for_update().get(pk=challenge.pk)
    if (
        challenge.token_digest != digest
        or challenge.consumed_at is not None
        or challenge.expires_at <= timezone.now()
        or not user.is_login_eligible
        or not user.has_usable_password()
        or not constant_time_compare(challenge.account_digest, account_digest(user))
    ):
        return False
    _set_password(user, password)
    return True


@transaction.atomic
def change_password(actor, current_password, password):
    lock_privilege_changes()
    user = User.objects.select_for_update().filter(pk=getattr(actor, "pk", None)).first()
    if user is None or not user.is_login_eligible:
        # Keep wrong/missing credentials on the same generic failure path.
        make_password(current_password)
        return False
    if not check_password(current_password, user.password):
        return False
    _set_password(user, password, actor=user)
    return True
