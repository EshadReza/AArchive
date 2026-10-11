"""Trusted policy adapters supply the same database predicate for lists/details.

Never register request-provided predicates or turn a grant into a final decision.
Each adapter owns assignment, privacy, lifecycle and field/projection ceilings.
"""

from dataclasses import dataclass
from types import MappingProxyType
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Model, Q

from apps.accounts.enums import PlatformRole
from apps.accounts.models import User

from .enums import CAPABILITY_SCOPES, ResourceKind
from .models import ScopedGrant


@dataclass(frozen=True)
class ResourceRef:
    kind: ResourceKind
    pk: UUID | int

    def __post_init__(self):
        if not isinstance(self.kind, ResourceKind) or not (
            isinstance(self.pk, UUID) or (type(self.pk) is int and self.pk > 0)
        ):
            raise ValueError(
                "Resource references require a typed kind and UUID or positive integer."
            )


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    roles: frozenset[str]


@dataclass(frozen=True)
class ResourcePolicy:
    model: type[Model]
    selectors: dict  # action -> callable(Principal) -> Q; trusted startup configuration only.

    def __post_init__(self):
        object.__setattr__(self, "selectors", MappingProxyType(dict(self.selectors)))


_policies = {}
_ADMIN_ACTIONS = frozenset({"users.manage", "roles.manage", "system.manage", "audit.view"})


def register_policy(kind, policy):
    if not isinstance(kind, ResourceKind) or not isinstance(policy, ResourcePolicy):
        raise TypeError("Register a typed resource policy.")
    if kind in _policies:
        raise ValueError("A resource policy is already registered.")
    if not issubclass(policy.model, Model) or not all(
        isinstance(action, str) and callable(selector)
        for action, selector in policy.selectors.items()
    ):
        raise TypeError("Invalid resource policy.")
    _policies[kind] = policy


def current_principal(actor):
    """Accept platform Users only; refetch roles/state for every authorization call."""
    if not isinstance(actor, User) or actor._state.adding:
        return None
    user = User.objects.eligible_for_authentication().filter(pk=actor.pk).first()
    if user is None:
        return None
    return Principal(user.pk, frozenset(user.role_assignments.values_list("role", flat=True)))


def scope_queryset(actor, action, queryset, *, kind):
    policy = _policies.get(kind) if isinstance(kind, ResourceKind) else None
    principal = current_principal(actor)
    if (
        policy is None
        or policy.model is not queryset.model
        or principal is None
        or action not in policy.selectors
    ):
        return queryset.none()
    predicate = policy.selectors[action](principal)
    if not isinstance(predicate, Q):
        raise TypeError("Policy selectors must return a database Q predicate.")
    return queryset.filter(predicate).distinct()


def allows(actor, action, resource=None):
    if resource is not None:
        if not isinstance(resource, ResourceRef):
            return False
        policy = _policies.get(resource.kind)
        if policy is None:
            return False
        try:
            return (
                scope_queryset(
                    actor, action, policy.model._default_manager.all(), kind=resource.kind
                )
                .filter(pk=resource.pk)
                .exists()
            )
        except ValueError, ValidationError, OverflowError:
            return False
    principal = current_principal(actor)
    if principal is None:
        return False
    if action in _ADMIN_ACTIONS:
        return PlatformRole.ADMINISTRATOR in principal.roles
    if action in {"contest.create", "course.create"}:
        return bool(principal.roles & {PlatformRole.ADMINISTRATOR, PlatformRole.TEACHER})
    return False


def require_permission(actor, action, resource=None):
    if not allows(actor, action, resource):
        raise PermissionDenied("Permission denied.")


def scope_exists(resource):
    """Resource registration/existence is required before creating a delegation."""
    policy = _policies.get(resource.kind)
    return policy is not None and policy.model._default_manager.filter(pk=resource.pk).exists()


def granted_scope_ids(principal, capability, kind):
    """Candidate scopes only. Adapters MUST intersect required assignments/privacy.

    Call with the fresh Principal supplied to a selector; never cache for a worker.
    """
    if PlatformRole.TEACHER not in principal.roles or CAPABILITY_SCOPES.get(capability) != kind:
        return ScopedGrant.objects.none().values_list("scope_id", flat=True)
    return ScopedGrant.objects.filter(
        subject_id=principal.user_id, capability=capability, scope_kind=kind, active=True
    ).values_list("scope_id", flat=True)
