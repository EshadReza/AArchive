"""Run isolated Django/Vite processes and verify health, cookies and CSRF end to end.

Run with the locked Python environment and installed frontend dependencies. Uses
ephemeral loopback ports; it does not stop or reuse a developer's existing servers.
The special CSRF probe lives in a test-only URLconf, never the application routes.
"""

import http.cookiejar
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPCookieProcessor, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    npm = shutil.which("npm")
    if npm is None:
        raise SystemExit("npm is required; install frontend dependencies with npm ci first.")
    backend_port = free_port()
    frontend_port = free_port()
    while frontend_port == backend_port:
        frontend_port = free_port()
    origin = f"http://127.0.0.1:{frontend_port}"
    env = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "backend"),
        "DJANGO_SETTINGS_MODULE": "config.settings.development",
        "DJANGO_ALLOWED_HOSTS": "127.0.0.1",
        "DJANGO_CSRF_TRUSTED_ORIGINS": "",
        "AARCHIVE_API_TARGET": f"http://127.0.0.1:{backend_port}",
    }
    django_command = (
        "import django; django.setup(); "
        "from django.conf import settings; settings.ROOT_URLCONF='tests.proxy_urls'; "
        "from django.core.management import call_command; "
        f"call_command('runserver','127.0.0.1:{backend_port}',use_reloader=False)"
    )
    processes = []
    with tempfile.TemporaryFile() as logs:
        try:
            for command, cwd in [
                ([sys.executable, "-c", django_command], ROOT),
                (
                    [npm, "run", "dev", "--", "--port", str(frontend_port), "--strictPort"],
                    ROOT / "frontend",
                ),
            ]:
                processes.append(
                    subprocess.Popen(
                        command,
                        cwd=cwd,
                        env=env,
                        stdout=logs,
                        stderr=logs,
                        start_new_session=True,
                    )
                )
            cookies = http.cookiejar.CookieJar()
            client = build_opener(HTTPCookieProcessor(cookies))
            deadline = time.monotonic() + 30
            while True:
                if any(process.poll() is not None for process in processes):
                    raise RuntimeError("A development server exited before the smoke check.")
                try:
                    with client.open(origin + "/api/health", timeout=2) as response:
                        assert response.status == 200
                        assert json.load(response) == {"status": "ok"}
                    break
                except URLError, TimeoutError:
                    if time.monotonic() >= deadline:
                        raise RuntimeError(
                            "Timed out waiting for the proxied health endpoint."
                        ) from None
                    time.sleep(0.2)
            url = origin + "/api/__test__/csrf"
            with client.open(url, timeout=5) as response:
                assert json.load(response)["host"] == f"127.0.0.1:{frontend_port}"
            token = next(cookie.value for cookie in cookies if cookie.name == "csrftoken")

            def post(headers):
                request = Request(
                    url, data=b"{}", headers={"Content-Type": "application/json", **headers}
                )
                try:
                    with client.open(request, timeout=5) as response:
                        return response.status, json.load(response)
                except HTTPError as error:
                    return error.code, None

            assert post({"Origin": origin})[0] == 403, "Missing CSRF token was accepted"
            status, body = post(
                {
                    "Origin": origin,
                    "X-CSRFToken": token,
                    "Cookie": f"csrftoken={token}; sessionid=synthetic-session",
                }
            )
            assert status == 200 and body["cookie_forwarded"], "Valid CSRF/cookie forwarding failed"
            assert post({"Origin": "https://foreign.invalid", "X-CSRFToken": token})[0] == 403
            print(
                "PASS: proxied health, original Host, cookie forwarding, valid CSRF, "
                "missing-token and foreign-origin rejection."
            )
        finally:
            for process in reversed(processes):
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)


if __name__ == "__main__":
    main()
