import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac

from apps.access.services import lock_privilege_changes
from apps.accounts.models import EmailVerification, User
from apps.audit.services import record_event

logger = logging.getLogger(__name__)


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def account_digest(user):
    return salted_hmac(
        "verification.account", user.email + "\0" + user.password, algorithm="sha256"
    ).hexdigest()


def allowed(email):
    return email.rsplit("@", 1)[-1] in settings.INSTITUTIONAL_EMAIL_DOMAINS


def deliver(email, token):
    # Fixed configured origin; never trust the request Host. Fragment stays out of HTTP logs.
    link = f"{settings.PUBLIC_APP_ORIGIN}/verify-email#token={token}"
    try:
        sent = send_mail(
            "Verify your AArchive email",
            "You requested an AArchive Student account. To confirm your email, open:\n"
            f"{link}\n\nThis link expires in {settings.VERIFICATION_TOKEN_SECONDS // 60} minutes. "
            "Only verify if you requested this account. Otherwise ignore this message. "
            "Verification may still require administrator approval.\n",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        if sent != 1:
            logger.warning("Verification mail was not delivered; the user may request a new link.")
    except Exception:
        # Account remains pending; no SMTP exception, address, token or password in logs/responses.
        logger.warning("Verification mail was not delivered; the user may request a new link.")


def issue(user):
    token = secrets.token_urlsafe(32)
    EmailVerification.objects.update_or_create(
        user=user,
        defaults={
            "token_digest": token_digest(token),
            "account_digest": account_digest(user),
            "consumed_at": None,
            "expires_at": timezone.now() + timedelta(seconds=settings.VERIFICATION_TOKEN_SECONDS),
        },
    )
    record_event(
        system_actor="authentication",
        action="auth.verification.issued",
        target_id=user.pk,
        new_value={"outcome": "issued"},
    )
    transaction.on_commit(lambda: deliver(user.email, token))


def register(*, email, password, display_name):
    if not allowed(email):
        User().set_password(password)
        return
    with transaction.atomic():
        lock_privilege_changes()
        if User.objects.filter(email=email).exists():
            User().set_password(password)
            return
        try:
            with transaction.atomic():
                user = User.objects.create_user(email, password, display_name=display_name)
        except ValidationError, IntegrityError:
            # Includes a concurrent trusted creation; never mutate that account.
            return
        user.approval_required = settings.REGISTRATION_REQUIRE_APPROVAL
        user.save(update_fields=["approval_required"])
        record_event(
            system_actor="authentication",
            action="auth.registration.created",
            target_id=user.pk,
            new_value={"state": "PENDING"},
        )
        issue(user)


@transaction.atomic
def resend(email):
    if not allowed(email):
        return
    lock_privilege_changes()
    user = User.objects.select_for_update().filter(email=email).first()
    if (
        user is None
        or user.state != "PENDING"
        or user.email_verified_at is not None
        or not EmailVerification.objects.filter(user=user, consumed_at__isnull=True).exists()
    ):
        return
    issue(user)


@transaction.atomic
def verify(token):
    lock_privilege_changes()
    digest = token_digest(token)
    challenge = EmailVerification.objects.filter(token_digest=digest).first()
    if challenge is None:
        return False
    user = User.objects.select_for_update().get(pk=challenge.user_id)
    challenge = EmailVerification.objects.select_for_update().get(pk=challenge.pk)
    now = timezone.now()
    if (
        challenge.token_digest != digest
        or not constant_time_compare(challenge.account_digest, account_digest(user))
        or challenge.consumed_at is not None
        or challenge.expires_at <= now
        or user.state != "PENDING"
        or user.email_verified_at is not None
        or not allowed(user.email)
    ):
        return False
    user.email_verified_at = now
    if not user.approval_required or user.approved_at is not None:
        user.state = "ACTIVE"
    user.save(update_fields=["email_verified_at", "state", "updated_at"])
    challenge.consumed_at = now
    challenge.save(update_fields=["consumed_at"])
    record_event(
        system_actor="authentication",
        action="auth.verification.completed",
        target_id=user.pk,
        new_value={"outcome": "verified"},
    )
    if user.state == "ACTIVE":
        record_event(
            system_actor="authentication",
            action="accounts.state.changed",
            target_id=user.pk,
            previous_value={"state": "PENDING"},
            new_value={"state": "ACTIVE"},
        )
    return True
