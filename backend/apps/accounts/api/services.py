import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare

from apps.access.policy import current_principal, require_permission
from apps.access.services import lock_privilege_changes, set_roles
from apps.accounts.models import Invitation, User
from apps.accounts.recovery.lifecycle import StateConflict
from apps.accounts.registration.services import account_digest, token_digest
from apps.audit.services import record_event

logger = logging.getLogger(__name__)


class AccountConflict(ValidationError):
    pass


class InvitationCooldown(ValidationError):
    pass


def deliver(email, token):
    link = f"{settings.PUBLIC_APP_ORIGIN}/accept-invitation#token={token}"
    try:
        sent = send_mail(
            "Your AArchive account invitation",
            "An administrator invited you to AArchive. Confirm your email and choose your own "
            f"password here:\n{link}\n\n"
            f"This link expires in {settings.INVITATION_SECONDS} seconds. "
            "If you did not expect this invitation, contact your institution. "
            "Administrator approval may still be required.\n",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        if sent != 1:
            logger.warning("Invitation mail was not delivered; an administrator may resend it.")
    except Exception:
        logger.warning("Invitation mail was not delivered; an administrator may resend it.")


def issue(actor, user):
    if not settings.INVITATIONS_ENABLED:
        raise ValidationError("Invitation delivery is not configured.")
    now = timezone.now()
    token = secrets.token_urlsafe(32)
    Invitation.objects.update_or_create(
        user=user,
        defaults={
            "token_digest": token_digest(token),
            "account_digest": account_digest(user),
            "expires_at": now + timedelta(seconds=settings.INVITATION_SECONDS),
            "consumed_at": None,
            "sent_at": now,
        },
    )
    record_event(
        actor=actor,
        action="accounts.invitation.issued",
        target_id=user.pk,
        new_value={"outcome": "issued"},
        reason="administrative_change",
    )
    transaction.on_commit(lambda: deliver(user.email, token))


@transaction.atomic
def create_account(*, actor, email, display_name, student_id, roles, approval_required):
    lock_privilege_changes()
    require_permission(actor, "users.manage")
    if type(approval_required) is not bool:
        raise ValidationError("Invalid approval flag.")
    # A manager creates only pending Students; explicit audited role service follows.
    try:
        with transaction.atomic():
            user = User.objects.create_user(email, display_name=display_name, student_id=student_id)
    except ValidationError, IntegrityError:
        raise AccountConflict("Check the identity fields; an account may already exist.") from None
    user.approval_required = approval_required
    user.save(update_fields=["approval_required"])
    record_event(
        actor=actor,
        action="accounts.admin.created",
        target_id=user.pk,
        new_value={"state": "PENDING"},
        reason="administrative_change",
    )
    set_roles(actor=actor, subject_id=user.pk, roles=roles, reason="administrative_change")
    issue(actor, user)
    return user


@transaction.atomic
def resend_invitation(*, actor, subject_id):
    lock_privilege_changes()
    require_permission(actor, "users.manage")
    user = User.objects.select_for_update().get(pk=subject_id)
    challenge = Invitation.objects.filter(user=user).first()
    if (
        challenge is None
        or user.state != "PENDING"
        or user.has_usable_password()
        or user.email_verified_at is not None
        or challenge.consumed_at is not None
    ):
        raise ValidationError("This account cannot receive an invitation.")
    if challenge.sent_at + timedelta(seconds=settings.INVITATION_RESEND_SECONDS) > timezone.now():
        raise InvitationCooldown("Wait before sending another invitation.")
    issue(actor, user)


@transaction.atomic
def accept_invitation(*, token, password):
    if not settings.INVITATIONS_ENABLED:
        return False
    lock_privilege_changes()
    digest = token_digest(token)
    challenge = Invitation.objects.filter(token_digest=digest).first()
    if challenge is None:
        return False
    user = User.objects.select_for_update().get(pk=challenge.user_id)
    challenge = Invitation.objects.select_for_update().get(pk=challenge.pk)
    if (
        challenge.token_digest != digest
        or challenge.consumed_at is not None
        or challenge.expires_at <= timezone.now()
        or user.state != "PENDING"
        or user.has_usable_password()
        or user.email_verified_at is not None
        or not constant_time_compare(challenge.account_digest, account_digest(user))
    ):
        return False
    validate_password(password, user)
    user.set_password(password)
    user.email_verified_at = timezone.now()
    if not user.approval_required or user.approved_at is not None:
        user.state = "ACTIVE"
    user.save(update_fields=["password", "email_verified_at", "state", "updated_at"])
    challenge.consumed_at = timezone.now()
    challenge.save(update_fields=["consumed_at"])
    record_event(
        system_actor="authentication",
        action="accounts.invitation.accepted",
        target_id=user.pk,
        new_value={"outcome": "accepted"},
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


@transaction.atomic
def update_profile(*, actor, display_name):
    lock_privilege_changes()
    if current_principal(actor) is None:
        raise PermissionDenied("Permission denied.")
    user = User.objects.select_for_update().get(pk=actor.pk)
    profile = user.profile
    if profile.display_name != display_name:
        profile.display_name = display_name
        profile.full_clean()
        profile.save(update_fields=["display_name", "updated_at"])
        record_event(
            actor=user,
            action="accounts.profile.changed",
            target_id=user.pk,
            new_value={"outcome": "updated"},
            reason="user_request",
        )
    return user


@transaction.atomic
def change_roles(*, actor, subject_id, roles, expected_roles, reason):
    lock_privilege_changes()
    require_permission(actor, "roles.manage")
    user = User.objects.select_for_update().get(pk=subject_id)
    current = sorted(user.role_assignments.values_list("role", flat=True))
    if sorted(expected_roles) != current:
        raise StateConflict("Roles changed; reload before reviewing.")
    return set_roles(actor=actor, subject_id=subject_id, roles=roles, reason=reason)
