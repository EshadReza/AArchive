"""Synthetic account state changes for the isolated S008 browser suite only."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def main():
    import django
    django.setup()
    from django.conf import settings
    from apps.accounts.models import User
    if (os.environ.get("DJANGO_SETTINGS_MODULE") != "config.settings.test"
            or not settings.DATABASES["default"]["NAME"].startswith("test_auth_browser_")):
        raise SystemExit("Fixture operations require the isolated browser-test database.")
    action, project = sys.argv[1:]
    if action not in {"suspend", "restore"} or project not in {"desktop", "mobile"}:
        raise SystemExit("Unknown fixture operation.")
    User.objects.filter(email=f"browser-{project}@iut.example").update(
        state="SUSPENDED" if action == "suspend" else "ACTIVE")


if __name__ == "__main__":
    main()
