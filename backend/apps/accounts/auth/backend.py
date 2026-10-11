from django.contrib.auth.backends import BaseBackend

from apps.accounts.models import User


class PlatformBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None):
        if not isinstance(email, str) or not isinstance(password, str):
            return None
        user = User.objects.filter(email=User.objects.normalize_email(email)).first()
        if user is None or not user.has_usable_password():
            # Equal-cost hash work for missing and invitation-only credentials.
            User().set_password(password)
            return None
        if user.check_password(password) and user.is_login_eligible:
            return user
        return None

    def get_user(self, user_id):
        # Django first validates the session/password hash. Middleware then flushes
        # ineligible accounts, so their old session cannot revive after restoration.
        return User.objects.filter(pk=user_id).first()
