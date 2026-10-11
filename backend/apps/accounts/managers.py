from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.hashers import identify_hasher
from django.core.exceptions import ValidationError
from django.db import models, transaction

from .enums import AUTHENTICATABLE_STATES, PlatformRole


def normalize_student_id(value):
    """Keep identifiers as strings (including leading zeroes); absence is SQL NULL."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError({"student_id": "Student IDs must be strings."})
    return value.strip().upper() or None


class UserQuerySet(models.QuerySet):
    def eligible_for_authentication(self):
        """Query current state; do not reuse cached account objects after revocation."""
        return self.filter(
            models.Q(approval_required=False) | models.Q(approved_at__isnull=False),
            state__in=AUTHENTICATABLE_STATES,
            email_verified_at__isnull=False,
        )


class UserManager(BaseUserManager.from_queryset(UserQuerySet)):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        # Institutional login treats the entire address case-insensitively.
        if not isinstance(email, str):
            raise ValidationError({"email": "An email address is required."})
        return email.strip().lower()

    def get_by_natural_key(self, username):
        return self.get(email=self.normalize_email(username))

    async def aget_by_natural_key(self, username):
        return await self.aget(email=self.normalize_email(username))

    def create_user(self, email, password=None, *, display_name="", student_id=None):
        """Create a pending Student only; no imported fields or privilege kwargs.

        Role/state mutation belongs to the audited services in S007/S010. This is
        a trusted account-construction primitive, not an importer or public API.
        """
        if password is not None:
            if not isinstance(password, str) or not password:
                raise ValidationError({"password": "Supply a nonempty raw password or None."})
            try:
                identify_hasher(password)
            except ValueError:
                pass
            else:
                raise ValidationError({"password": "Encoded password hashes are not accepted."})
        from .models import UserProfile, UserRole

        user = self.model(
            email=self.normalize_email(email), student_id=normalize_student_id(student_id)
        )
        if password is None:
            user.set_unusable_password()
        else:
            user.set_password(password)
        with transaction.atomic(using=self.db):
            user.full_clean()
            user.save(using=self.db)
            profile = UserProfile(user=user, display_name=display_name)
            profile.full_clean()
            profile.save(using=self.db)
            UserRole.objects.using(self.db).create(user=user, role=PlatformRole.STUDENT)
        return user
