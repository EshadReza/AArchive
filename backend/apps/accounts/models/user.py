import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.db.models.functions import Lower, Trim, Upper
from django.utils import timezone

from ..enums import AUTHENTICATABLE_STATES, AccountState, PlatformRole
from ..managers import UserManager, normalize_student_id


class User(AbstractBaseUser):
    """Platform identity only. Source snapshots and source credentials live elsewhere."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    student_id = models.CharField(max_length=64, unique=True, null=True, blank=True)
    state = models.CharField(max_length=16, choices=AccountState, default=AccountState.PENDING)
    state_before_restriction = models.CharField(max_length=16, blank=True, default="")
    email_verified_at = models.DateTimeField(null=True, blank=True)
    approval_required = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    state_before_restriction__in=["", "PENDING", *AUTHENTICATABLE_STATES]
                ),
                name="account_prior_state_known",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(email=Lower(Trim("email")))
                    & ~models.Q(email="")
                    & ~models.Q(email__regex=r"\s")
                ),
                name="account_email_canonical",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(student_id__isnull=True)
                    | (
                        models.Q(student_id=Upper(Trim("student_id")))
                        & ~models.Q(student_id="")
                        & ~models.Q(student_id__regex=r"^\s|\s$")
                    )
                ),
                name="account_student_id_canonical",
            ),
            models.CheckConstraint(
                condition=models.Q(state__in=AccountState.values), name="account_state_known"
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(state__in=AUTHENTICATABLE_STATES)
                    | (
                        models.Q(email_verified_at__isnull=False)
                        & (models.Q(approval_required=False) | models.Q(approved_at__isnull=False))
                    )
                ),
                name="account_eligible_state_verified",
            ),
        ]

    def clean(self):
        super().clean()
        self.email = UserManager.normalize_email(self.email)
        self.student_id = normalize_student_id(self.student_id)

    def save(self, *args, **kwargs):
        self.email = UserManager.normalize_email(self.email)
        self.student_id = normalize_student_id(self.student_id)
        return super().save(*args, **kwargs)

    @property
    def is_login_eligible(self):
        return (
            self.state in AUTHENTICATABLE_STATES
            and self.email_verified_at is not None
            and (not self.approval_required or self.approved_at is not None)
        )

    @property
    def is_active(self):
        # Django authentication must not confuse INACTIVE (inactivity) with suspension.
        return self.is_login_eligible

    @property
    def allows_authenticated_session(self):
        return self.is_login_eligible

    @property
    def allows_historical_access(self):
        # An eligibility ceiling, never an object-level permission grant.
        return self.is_login_eligible


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, primary_key=True, on_delete=models.PROTECT, related_name="profile"
    )
    display_name = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)


class UserRole(models.Model):
    """Fixed platform vocabulary; scoped grants and audited edits arrive in S007."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="role_assignments"
    )
    role = models.CharField(max_length=16, choices=PlatformRole)
    assigned_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="account_role_once"),
            models.CheckConstraint(
                condition=models.Q(role__in=PlatformRole.values), name="account_role_known"
            ),
        ]
