from django.db import models


class LoginAttempt(models.Model):
    # Keyed digests, not email/IP plaintext. Fixed-window counters are shared by workers.
    key = models.CharField(max_length=64, primary_key=True)
    attempts = models.PositiveIntegerField(default=0)
    resets_at = models.DateTimeField(db_index=True)
