"""Database session revocation, including sessions issued before this sprint."""

from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.models import Session
from django.utils import timezone


def revoke_sessions(user):
    # Caller holds the privilege/user locks used by sign_in. Decode in bounded
    # batches because Django's session payload has no relational user index.
    keys = []
    for session in Session.objects.filter(expire_date__gt=timezone.now()).iterator(chunk_size=200):
        if session.get_decoded().get(SESSION_KEY) == str(user.pk):
            keys.append(session.pk)
            if len(keys) == 200:
                Session.objects.filter(pk__in=keys).delete()
                keys.clear()
    if keys:
        Session.objects.filter(pk__in=keys).delete()
