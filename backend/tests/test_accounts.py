"""Account boundaries exercised against PostgreSQL, including ORM bypasses."""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from apps.accounts.enums import AccountState, PlatformRole
from apps.accounts.models import User, UserProfile, UserRole

pytestmark = pytest.mark.django_db


def test_custom_user_schema_and_pending_student_creation():
    user = User.objects.create_user(
        " Learner@IUT.EXAMPLE ", student_id=" 001a ", display_name="Test Learner"
    )
    assert get_user_model() is User
    assert "auth_user" not in connection.introspection.table_names()
    assert isinstance(user.pk, uuid.UUID)
    assert user.email == "learner@iut.example"
    assert user.student_id == "001A"
    assert user.profile.display_name == "Test Learner"
    assert list(user.role_assignments.values_list("role", flat=True)) == [PlatformRole.STUDENT]
    assert user.state == AccountState.PENDING
    assert user.email_verified_at is None
    assert not user.has_usable_password()
    assert not user.is_active
    assert User.objects.get_by_natural_key(" LEARNER@IUT.EXAMPLE ") == user


def test_password_is_hashed_and_verified_by_django():
    raw_password = "synthetic-password-only-123"
    user = User.objects.create_user("learner@iut.example", raw_password)
    assert user.password != raw_password
    assert user.check_password(raw_password)
    assert not user.check_password("wrong-password")
    assert not user.is_login_eligible  # Correct password alone cannot activate an account.


def test_encoded_password_is_rejected():
    with pytest.raises(ValidationError, match="Encoded password hashes"):
        User.objects.create_user("learner@iut.example", make_password("synthetic-only"))
    assert not User.objects.exists()


@pytest.mark.parametrize(
    "field", ["state", "role", "source_roles", "password_hash", "is_superuser"]
)
def test_creation_cannot_mass_assign_source_fields_or_privileges(field):
    with pytest.raises(TypeError):
        User.objects.create_user("learner@iut.example", **{field: "ADMINISTRATOR"})
    assert not User.objects.exists()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"email": "not-an-email"},
        {"email": None},
        {"student_id": 123},
        {"password": ""},
        {"password": 123},
        {"display_name": "x" * 201},
    ],
)
def test_invalid_creation_leaves_no_partial_account(kwargs):
    with pytest.raises(ValidationError):
        User.objects.create_user(**({"email": "learner@iut.example"} | kwargs))
    assert not User.objects.exists()
    assert not UserProfile.objects.exists()
    assert not UserRole.objects.exists()


@pytest.mark.parametrize(
    ("state", "eligible"),
    [
        (AccountState.PENDING, False),
        (AccountState.ACTIVE, True),
        (AccountState.INACTIVE, True),
        (AccountState.GRADUATED, True),
        (AccountState.ALUMNI, True),
        (AccountState.SUSPENDED, False),
        (AccountState.ARCHIVED, False),
        (AccountState.ANONYMIZED, False),
    ],
)
def test_state_eligibility_and_retained_identity(state, eligible):
    user = User.objects.create_user("learner@iut.example")
    original_id = user.pk
    # Trusted fixture writes; audited transitions are the S010 service's responsibility.
    User.objects.filter(pk=user.pk).update(state=state, email_verified_at=timezone.now())
    user.refresh_from_db()
    assert user.is_login_eligible is eligible
    assert user.is_active is eligible
    assert user.allows_authenticated_session is eligible
    assert user.allows_historical_access is eligible
    assert User.objects.eligible_for_authentication().filter(pk=user.pk).exists() is eligible
    assert user.pk == original_id
    assert user.profile.pk == original_id
    assert user.role_assignments.count() == 1


@pytest.mark.parametrize(
    "verification",
    [
        {"email_verified_at": None},
        {"email_verified_at": timezone.now(), "approval_required": True, "approved_at": None},
    ],
)
def test_eligible_states_require_verification_and_required_approval(verification):
    user = User.objects.create_user("learner@iut.example")
    for field, value in verification.items():
        setattr(user, field, value)
    user.state = AccountState.ACTIVE
    assert not user.is_login_eligible
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(state=AccountState.ACTIVE, **verification)


def test_approval_allows_activation_but_later_suspension_is_seen_by_fresh_queries():
    user = User.objects.create_user("learner@iut.example")
    User.objects.filter(pk=user.pk).update(
        state=AccountState.ACTIVE,
        email_verified_at=timezone.now(),
        approval_required=True,
        approved_at=timezone.now(),
    )
    assert User.objects.eligible_for_authentication().get(pk=user.pk).is_active
    User.objects.filter(pk=user.pk).update(state=AccountState.SUSPENDED)
    assert not User.objects.eligible_for_authentication().filter(pk=user.pk).exists()
    user.refresh_from_db()
    assert not user.allows_authenticated_session


@pytest.mark.parametrize(
    "kwargs",
    [{"email": " FIRST@IUT.EXAMPLE "}, {"email": "other@iut.example", "student_id": " 001a "}],
)
def test_manager_rejects_normalized_duplicates(kwargs):
    User.objects.create_user("first@iut.example", student_id="001A")
    with pytest.raises(ValidationError):
        User.objects.create_user(**kwargs)
    assert User.objects.count() == 1


@pytest.mark.parametrize("field", ["email", "student_id"])
def test_database_rejects_duplicates_even_without_model_validation(field):
    first = User.objects.create_user("first@iut.example", student_id="001A")
    second = User.objects.create_user("second@iut.example", student_id="002A")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=second.pk).update(**{field: getattr(first, field)})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "UPPER@iut.example"),
        ("email", " padded@iut.example "),
        ("email", "tab\t@iut.example"),
        ("email", ""),
        ("student_id", "001a"),
        ("student_id", " 001A "),
        ("student_id", "\t001A"),
        ("student_id", "001A\n"),
        ("student_id", ""),
        ("state", "DELETED"),
    ],
)
def test_database_rejects_noncanonical_identifiers_and_unknown_state(field, value):
    user = User.objects.create_user("learner@iut.example")
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(**{field: value})


def test_absent_student_ids_are_distinct_nulls():
    users = [
        User.objects.create_user(f"learner{index}@iut.example", student_id=value)
        for index, value in enumerate([None, "", "   "])
    ]
    assert len({user.pk for user in users}) == 3
    assert User.objects.filter(student_id__isnull=True).count() == 3


def test_fixed_roles_allow_multiple_assignments_but_reject_duplicates_and_source_roles():
    user = User.objects.create_user("learner@iut.example")
    UserRole.objects.create(user=user, role=PlatformRole.TEACHER)
    UserRole.objects.create(user=user, role=PlatformRole.ADMINISTRATOR)
    assert set(user.role_assignments.values_list("role", flat=True)) == set(PlatformRole.values)
    for role in [PlatformRole.STUDENT, "SOURCE_ADMIN", "TA"]:
        with pytest.raises(IntegrityError), transaction.atomic():
            UserRole.objects.create(user=user, role=role)


def test_account_references_prevent_ordinary_deletion():
    user = User.objects.create_user("learner@iut.example")
    with pytest.raises(ProtectedError):
        user.delete()
    assert User.objects.filter(pk=user.pk).exists()
    # The database also protects references if a caller bypasses Django's collector.
    with pytest.raises(IntegrityError), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM accounts_user WHERE id = %s", [user.pk])
            cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
