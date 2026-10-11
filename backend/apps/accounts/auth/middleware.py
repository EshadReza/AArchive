from django.contrib.auth import logout
from django.db import transaction

from apps.audit.services import record_event


class AccountSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Health remains database-independent even with a stale browser cookie.
        if request.path != "/api/health" and request.session.session_key:
            user = request.user
            if user.is_authenticated and not user.is_login_eligible:
                with transaction.atomic():
                    record_event(
                        system_actor="authentication",
                        action="auth.session.ended",
                        target_id=user.pk,
                        new_value={"outcome": "revoked"},
                    )
                    logout(request)
        return self.get_response(request)
