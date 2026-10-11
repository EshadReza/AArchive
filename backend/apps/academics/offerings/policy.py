from django.db.models import Q

from apps.access.enums import ResourceKind
from apps.access.policy import ResourcePolicy, register_policy

from .models import Offering


def available():
    return Q(
        archived=False,
        course__archived=False,
        course__department__archived=False,
        batch__archived=False,
        batch__department__archived=False,
        term__archived=False,
        section__archived=False,
    )


def selected(principal, *, write=False):
    if "ADMINISTRATOR" in principal.roles:
        scope = Q()
    elif "TEACHER" in principal.roles:
        scope = Q(
            teacher_assignments__teacher_id=principal.user_id,
            teacher_assignments__ended_at__isnull=True,
        )
    else:
        return Q(pk__in=[])
    return scope & available() if write else scope


def register():
    register_policy(
        ResourceKind.OFFERING,
        ResourcePolicy(
            Offering,
            {
                "course.view": selected,
                "course.manage": lambda principal: selected(principal, write=True),
            },
        ),
    )
