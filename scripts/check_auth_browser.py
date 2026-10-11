"""Real Django/Vite/Chromium login tests, in a uniquely named disposable database."""

import os
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen
from urllib.error import URLError

from check_dev_proxy import free_port

ROOT = Path(__file__).resolve().parents[1]


def main():
    if not os.environ.get("TEST_DATABASE_URL"):
        raise SystemExit("TEST_DATABASE_URL must select a disposable PostgreSQL server.")
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings.test"
    sys.path.insert(0, str(ROOT / "backend"))
    import django
    django.setup()
    from django.db import connection
    from django.utils import timezone
    from apps.accounts.models import User, UserRole
    name = "test_auth_browser_" + uuid.uuid4().hex[:12]
    connection.settings_dict["TEST"]["NAME"] = name
    connection.creation.create_test_db(verbosity=0, autoclobber=False, serialize=False)
    processes = []
    try:
        for project in ["desktop", "mobile"]:
            user = User.objects.create_user(f"browser-{project}@iut.example", "synthetic-browser-password-123",
                                            display_name="Test Member")
            User.objects.filter(pk=user.pk).update(state="ACTIVE", email_verified_at=timezone.now())
            for prefix in ["recovery", "lifecycle-admin"]:
                extra = User.objects.create_user(f"{prefix}-{project}@iut.example", "synthetic-browser-password-123", display_name="Recovery Member")
                User.objects.filter(pk=extra.pk).update(state="ACTIVE", email_verified_at=timezone.now())
                if prefix == "lifecycle-admin":
                    UserRole.objects.create(user=extra, role="ADMINISTRATOR")
        connection.close()
        backend_port, frontend_port = free_port(), free_port()
        while frontend_port == backend_port:
            frontend_port = free_port()
        parts = urlsplit(os.environ["TEST_DATABASE_URL"])
        db_url = urlunsplit((parts.scheme, parts.netloc, "/" + name, parts.query, ""))
        origin = f"http://127.0.0.1:{frontend_port}"
        env = {**os.environ, "TEST_DATABASE_URL": db_url, "AUTH_E2E_BASE_URL": origin,
               "AUTH_E2E_PYTHON": sys.executable, "AARCHIVE_API_TARGET": f"http://127.0.0.1:{backend_port}",
               "AUTH_LOGIN_ATTEMPT_LIMIT": "3", "AUTH_LOGIN_IP_LIMIT": "100", "AUTH_LOGIN_WINDOW_SECONDS": "10"}
        with tempfile.TemporaryDirectory(prefix="aarchive-test-mail-") as mailbox, tempfile.TemporaryFile() as logs:
            env.update({"AARCHIVE_TEST_MAIL_DIRECTORY": mailbox, "PUBLIC_APP_ORIGIN": origin,
                        "INSTITUTIONAL_EMAIL_DOMAINS": "iut.example", "REGISTRATION_REQUIRE_APPROVAL": "false",
                        "REGISTRATION_IP_LIMIT": "100", "RECOVERY_IP_LIMIT": "100", "PASSWORD_RESET_ENABLED": "true", "INVITATIONS_ENABLED": "true"})
            try:
                for command, directory in [
                    ([sys.executable, "backend/manage.py", "runserver", f"127.0.0.1:{backend_port}", "--noreload"], ROOT),
                    (["npm", "run", "dev", "--", "--port", str(frontend_port), "--strictPort"], ROOT / "frontend"),
                ]:
                    processes.append(subprocess.Popen(command, cwd=directory, env=env, stdout=logs,
                                                       stderr=logs, start_new_session=True))
                deadline = time.monotonic() + 30
                while True:
                    try:
                        with urlopen(origin + "/api/health", timeout=1) as response:
                            if response.status == 200:
                                break
                    except (URLError, TimeoutError):
                        pass
                    if time.monotonic() >= deadline or any(p.poll() is not None for p in processes):
                        raise RuntimeError("Authentication browser test servers did not become ready.")
                    time.sleep(0.1)
                subprocess.run(["npx", "--no-install", "playwright", "test", "--config=playwright.auth.config.ts"],
                               cwd=ROOT / "frontend", env=env, check=True)
            except BaseException:
                logs.seek(0)
                print(logs.read().decode(errors="replace")[-5000:], file=sys.stderr)
                raise
    finally:
        for process in processes:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
        connection.creation.destroy_test_db(verbosity=0)
    print("PASS: real authentication browser checks; isolated servers and database removed.")


if __name__ == "__main__":
    main()
