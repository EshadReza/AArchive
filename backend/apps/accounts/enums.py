from django.db import models


class AccountState(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACTIVE = "ACTIVE", "Active"
    INACTIVE = "INACTIVE", "Inactive"
    GRADUATED = "GRADUATED", "Graduated"
    ALUMNI = "ALUMNI", "Alumni"
    SUSPENDED = "SUSPENDED", "Suspended"
    ARCHIVED = "ARCHIVED", "Archived"
    ANONYMIZED = "ANONYMIZED", "Anonymized"


class PlatformRole(models.TextChoices):
    ADMINISTRATOR = "ADMINISTRATOR", "Administrator"
    TEACHER = "TEACHER", "Teacher"
    STUDENT = "STUDENT", "Student"


AUTHENTICATABLE_STATES = (
    AccountState.ACTIVE,
    AccountState.INACTIVE,
    AccountState.GRADUATED,
    AccountState.ALUMNI,
)
