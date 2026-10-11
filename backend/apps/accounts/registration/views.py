from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.response import Response

from apps.accounts.auth.views import AuthView
from apps.accounts.models import User

from . import services
from .throttle import consume_attempt


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if (
            not isinstance(data, dict)
            or set(data) != set(self.fields)
            or any(not isinstance(value, str) for value in data.values())
        ):
            raise serializers.ValidationError({"non_field_errors": ["Invalid fields."]})
        return super().to_internal_value(data)


class EmailInput(StrictSerializer):
    email = serializers.EmailField(max_length=254)

    def validate_email(self, value):
        return User.objects.normalize_email(value)


class RegistrationInput(EmailInput):
    display_name = serializers.CharField(max_length=200)
    password = serializers.CharField(max_length=1024, trim_whitespace=False, write_only=True)

    def validate(self, data):
        try:
            validate_password(data["password"], User(email=data["email"]))
        except DjangoValidationError:
            raise serializers.ValidationError(
                {"password": ["Password does not meet policy."]}
            ) from None
        return data


class TokenInput(StrictSerializer):
    token = serializers.RegexField(r"\A[A-Za-z0-9_-]{43}\Z", max_length=43)


@method_decorator(csrf_protect, name="dispatch")
class RegistrationView(AuthView):
    http_method_names = ["post"]
    serializer_class = RegistrationInput

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        retry = consume_attempt(data.get("email"), request.META.get("REMOTE_ADDR", "unknown"))
        if retry:
            return Response(
                {
                    "code": "registration_limited",
                    "message": "Too many attempts. Try again later.",
                    "request_id": None,
                },
                status=429,
                headers={"Retry-After": str(retry)},
            )
        return self.perform(data)

    def perform(self, data):
        services.register(**data)
        return self.accepted()

    @staticmethod
    def accepted():
        return Response(
            {
                "message": "If this address is eligible, a verification email will arrive. "
                "Check your inbox or request a new link."
            },
            status=202,
        )


class ResendView(RegistrationView):
    serializer_class = EmailInput

    def perform(self, data):
        services.resend(data["email"])
        return self.accepted()


class VerifyView(RegistrationView):
    serializer_class = TokenInput

    def perform(self, data):
        if not services.verify(data["token"]):
            return Response(
                {
                    "code": "verification_invalid",
                    "message": "This link is invalid or expired. Request a new link.",
                    "request_id": None,
                },
                status=400,
            )
        return Response(
            {
                "message": (
                    "Email verified. You can sign in once any required "
                    "administrator approval is complete."
                )
            }
        )
