from io import BytesIO

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import serializers
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import sign_in, sign_out


def csrf_failure(request, reason=""):
    return JsonResponse(
        {"code": "csrf_failed", "message": "Refresh the page and try again.", "request_id": None},
        status=403,
        headers={"Cache-Control": "no-store"},
    )


def account_data(user):
    if user is None or not user.is_authenticated:
        return None
    return {
        "id": str(user.pk),
        "email": user.email,
        "display_name": user.profile.display_name,
        "state": user.state,
        "roles": list(user.role_assignments.order_by("role").values_list("role", flat=True)),
    }


class Credentials(serializers.Serializer):
    email = serializers.CharField(max_length=254, trim_whitespace=True)
    password = serializers.CharField(max_length=1024, trim_whitespace=False, write_only=True)

    def to_internal_value(self, data):
        if (
            not isinstance(data, dict)
            or set(data) != {"email", "password"}
            or any(not isinstance(value, str) for value in data.values())
        ):
            raise serializers.ValidationError(
                {"non_field_errors": ["Only email and password are accepted."]}
            )
        return super().to_internal_value(data)


class AuthJSONParser(JSONParser):
    def parse(self, stream, media_type=None, parser_context=None):
        content = stream.read(8193)
        if len(content) > 8192:
            raise ParseError("Authentication request is too large.")
        return super().parse(BytesIO(content), media_type=media_type, parser_context=parser_context)


class AuthView(APIView):
    permission_classes = [AllowAny]
    parser_classes = [AuthJSONParser]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        response.data = {
            "code": "invalid_request" if response.status_code == 400 else "request_denied",
            "message": "The request could not be completed. Refresh and try again.",
            "request_id": None,
        }
        return response


@method_decorator(ensure_csrf_cookie, name="dispatch")
class SessionView(AuthView):
    http_method_names = ["get", "head"]

    def get(self, request):
        return Response({"user": account_data(request.user)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(AuthView):
    http_method_names = ["post"]

    def post(self, request):
        credentials = Credentials(data=request.data)
        credentials.is_valid(raise_exception=True)
        user, retry = sign_in(request._request, **credentials.validated_data)
        if retry:
            return Response(
                {
                    "code": "login_limited",
                    "message": "Too many sign-in attempts. Try again later.",
                    "request_id": None,
                },
                status=429,
                headers={"Retry-After": str(retry)},
            )
        if user is None:
            return Response(
                {
                    "code": "invalid_credentials",
                    "message": "Unable to sign in with those details.",
                    "request_id": None,
                },
                status=401,
            )
        return Response({"user": account_data(user)})


@method_decorator(csrf_protect, name="dispatch")
class LogoutView(AuthView):
    http_method_names = ["post"]

    def post(self, request):
        sign_out(request._request)
        return Response(status=204)
