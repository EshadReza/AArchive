from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response

from apps.access.policy import allows
from apps.accounts.auth.views import AuthView
from apps.accounts.models import User
from apps.accounts.registration.views import EmailInput, StrictSerializer, TokenInput
from apps.audit.services import record_event

from . import lifecycle, services
from .throttle import consume_attempt


class ResetInput(TokenInput):
    password = serializers.CharField(max_length=1024, trim_whitespace=False, write_only=True)


class ChangeInput(StrictSerializer):
    current_password = serializers.CharField(
        max_length=1024, trim_whitespace=False, write_only=True
    )
    password = serializers.CharField(max_length=1024, trim_whitespace=False, write_only=True)


@method_decorator(csrf_protect, name="dispatch")
class ResetRequestView(AuthView):
    http_method_names = ["post"]
    serializer_class = EmailInput

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        identity = data.get("email")
        if isinstance(self, ChangePasswordView):
            identity = str(request.user.pk)
        retry = consume_attempt(identity, request.META.get("REMOTE_ADDR", "unknown"))
        if retry:
            return Response(
                {
                    "code": "recovery_limited",
                    "message": "Too many attempts. Try again later.",
                    "request_id": None,
                },
                status=429,
                headers={"Retry-After": str(retry)},
            )
        try:
            return self.perform(request, data)
        except ValidationError:
            return Response(
                {
                    "code": "password_invalid",
                    "message": (
                        "Choose a different password with at least 12 characters. "
                        "Avoid common passwords, only numbers, or your email."
                    ),
                    "request_id": None,
                },
                status=400,
            )

    def perform(self, request, data):
        services.request_reset(data["email"])
        return Response(
            {
                "message": "If this account is eligible, a password reset email will arrive. "
                "Check your inbox or try again later."
            },
            status=202,
        )

    @staticmethod
    def failure(outcome):
        with transaction.atomic():
            record_event(
                system_actor="authentication",
                action="auth.recovery.failed",
                target_id="system",
                new_value={"outcome": outcome},
            )
        return Response(
            {
                "code": "recovery_invalid",
                "message": (
                    "Unable to complete this request. "
                    "Check your details or request a new reset link."
                ),
                "request_id": None,
            },
            status=400,
        )


class ResetConfirmView(ResetRequestView):
    serializer_class = ResetInput

    def perform(self, request, data):
        if not services.confirm_reset(data["token"], data["password"]):
            return self.failure("invalid_token")
        return Response(
            {
                "message": (
                    "Password updated. All sessions have ended. Sign in with your new password."
                )
            }
        )


class ChangePasswordView(ResetRequestView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangeInput

    def perform(self, request, data):
        if not services.change_password(request.user, data["current_password"], data["password"]):
            return self.failure("invalid_credentials")
        return Response(
            {
                "message": (
                    "Password updated. All sessions have ended. Sign in with your new password."
                )
            }
        )


class CanManageAccounts(BasePermission):
    def has_permission(self, request, view):
        return allows(request.user, "users.manage")


class LifecycleInput(StrictSerializer):
    command = serializers.ChoiceField(choices=[*lifecycle.TRANSITIONS, "approve", "restore"])
    expected_state = serializers.ChoiceField(
        choices=[
            "PENDING",
            "ACTIVE",
            "INACTIVE",
            "GRADUATED",
            "ALUMNI",
            "SUSPENDED",
            "ARCHIVED",
            "ANONYMIZED",
        ]
    )
    reason = serializers.ChoiceField(
        choices=["administrative_change", "user_request", "security_response"]
    )


@method_decorator(csrf_protect, name="dispatch")
class LifecycleView(AuthView):
    permission_classes = [CanManageAccounts]
    http_method_names = ["post"]

    def post(self, request, pk):
        serializer = LifecycleInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user = lifecycle.transition(
                actor=request.user, subject_id=pk, **serializer.validated_data
            )
        except User.DoesNotExist:
            return Response(
                {"code": "not_found", "message": "Account not found.", "request_id": None},
                status=404,
            )
        except lifecycle.StateConflict:
            return Response(
                {
                    "code": "state_conflict",
                    "message": "The account state changed. Refresh before retrying.",
                    "request_id": None,
                },
                status=409,
            )
        except ValidationError:
            return Response(
                {
                    "code": "transition_invalid",
                    "message": (
                        "This transition is not allowed. Check the account "
                        "prerequisites and administrator coverage."
                    ),
                    "request_id": None,
                },
                status=400,
            )
        return Response({"id": str(user.pk), "state": user.state})
