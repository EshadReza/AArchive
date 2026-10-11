import pytest
from django.test import override_settings
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView


def test_health_is_public_minimal_and_does_not_touch_database(client):
    # pytest-django forbids DB queries without a db fixture: this also proves liveness
    # does not become unavailable just because PostgreSQL is down.
    with override_settings(SECRET_KEY="must-not-appear-in-response"):
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response["Content-Type"] == "application/json"
    assert response["Cache-Control"] == "no-store"
    assert not response.cookies


def test_health_head_has_no_body(client):
    response = client.head("/api/health")
    assert response.status_code == 200
    assert response.content == b""
    assert response["Cache-Control"] == "no-store"


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_health_rejects_writes(client, method):
    response = getattr(client, method)("/api/health")
    assert response.status_code == 405
    assert response["Allow"] == "GET, HEAD"


def test_invalid_host_is_rejected(client):
    assert client.get("/api/health", HTTP_HOST="untrusted.invalid").status_code == 400


def test_unknown_routes_do_not_expose_debug_pages(client):
    response = client.get("/api/not-a-route")
    assert response.status_code == 404
    assert b"DEBUG" not in response.content


def test_new_api_views_are_denied_by_default():
    class FutureView(APIView):
        def get(self, request):
            return Response({"private": True})

    response = FutureView.as_view()(APIRequestFactory().get("/api/future"))
    assert response.status_code == 403
    assert "private" not in response.data
