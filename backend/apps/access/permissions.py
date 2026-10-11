from rest_framework.permissions import BasePermission

from .policy import allows


class PolicyPermission(BasePermission):
    """Global DRF action gate; views must also scope object querysets separately."""

    def has_permission(self, request, view):
        action = getattr(view, "policy_action", None)
        return isinstance(action, str) and allows(request.user, action)
