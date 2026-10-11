"""Only loaded by check_dev_proxy.py; never mounted in the application URLconf."""

from django.http import JsonResponse
from django.urls import path
from django.views.decorators.csrf import ensure_csrf_cookie

from config.urls import urlpatterns as application_urls


@ensure_csrf_cookie
def csrf_probe(request):
    return JsonResponse(
        {
            "ok": True,
            "host": request.get_host(),
            "cookie_forwarded": request.COOKIES.get("sessionid") == "synthetic-session",
        }
    )


urlpatterns = [*application_urls, path("api/__test__/csrf", csrf_probe)]
