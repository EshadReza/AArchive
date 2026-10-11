from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.access.policy import current_principal
from apps.accounts.auth.views import AuthView
from apps.accounts.enums import AccountState, PlatformRole
from apps.accounts.models import Invitation, User
from apps.accounts.recovery.throttle import consume_attempt
from apps.accounts.recovery.views import CanManageAccounts, ResetInput

from . import services


def account_data(user):
    try:
        invitation = user.invitation
    except Invitation.DoesNotExist:
        invitation = None
    return {
        "invitation_pending": bool(
            invitation
            and invitation.consumed_at is None
            and user.state == "PENDING"
            and not user.has_usable_password()
            and user.email_verified_at is None
        ),
        "id": str(user.pk),
        "email": user.email,
        "display_name": user.profile.display_name,
        "student_id": user.student_id,
        "roles": sorted(row.role for row in user.role_assignments.all()),
        "state": user.state,
        "approval_required": user.approval_required,
        "email_verified": user.email_verified_at is not None,
        "approved": user.approved_at is not None,
        "date_joined": user.date_joined.isoformat(),
    }


class StrictFields(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, dict) or set(data) != set(self.fields):
            raise ValidationError({"non_field_errors": ["Supply exactly the documented fields."]})
        for key, value in data.items():
            field = self.fields[key]
            if isinstance(field, serializers.CharField) and not (
                isinstance(value, str) or value is None and field.allow_null
            ):
                raise ValidationError({key: ["A string is required."]})
            if isinstance(field, serializers.BooleanField) and type(value) is not bool:
                raise ValidationError({key: ["A boolean is required."]})
        return super().to_internal_value(data)


class RolesField(serializers.ListField):
    def __init__(self, **kwargs):
        super().__init__(
            child=serializers.ChoiceField(choices=PlatformRole.values),
            min_length=1,
            max_length=3,
            **kwargs,
        )

    def to_internal_value(self, data):
        values = super().to_internal_value(data)
        if len(set(values)) != len(values):
            raise ValidationError("Roles must be distinct.")
        return values


class CreateInput(StrictFields):
    email = serializers.EmailField(max_length=254)
    display_name = serializers.CharField(max_length=200)
    student_id = serializers.CharField(max_length=64, allow_null=True, allow_blank=True)
    roles = RolesField()
    approval_required = serializers.BooleanField()


class RoleInput(StrictFields):
    roles = RolesField()
    expected_roles = RolesField()
    reason = serializers.ChoiceField(
        choices=["administrative_change", "user_request", "security_response"]
    )


class ProfileInput(StrictFields):
    display_name = serializers.CharField(max_length=200)


class Pagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


@method_decorator(csrf_protect, name="dispatch")
class AccountView(AuthView):
    permission_classes = [CanManageAccounts]

    def handle_exception(self, exc):
        if isinstance(exc, User.DoesNotExist):
            exc = NotFound("Account not found.")
        if isinstance(exc, services.StateConflict):
            return self.error(
                "account_conflict", "This account changed. Reload and review again.", 409
            )
        if isinstance(exc, services.AccountConflict):
            return self.error(
                "account_conflict",
                "Check the email and student ID; an account may already exist.",
                409,
            )
        if isinstance(exc, services.InvitationCooldown):
            response = self.error(
                "invitation_limited", "Wait before sending another invitation.", 429
            )
            response["Retry-After"] = str(settings.INVITATION_RESEND_SECONDS)
            return response
        if isinstance(exc, DjangoValidationError):
            return self.error(
                "account_invalid",
                (
                    "This action is not allowed. Check account prerequisites, "
                    "roles and mail configuration."
                ),
                400,
            )
        response = super().handle_exception(exc)
        if isinstance(exc, serializers.ValidationError):
            response.data["message"] = "Check the submitted fields and try again."
            # Serializer messages are bounded, never model/database exception text.
            response.data["field_errors"] = {
                key: ["Check this field."]
                for key in exc.detail
                if key
                in {
                    "email",
                    "display_name",
                    "student_id",
                    "roles",
                    "approval_required",
                    "password",
                    "token",
                }
            }
        return response

    @staticmethod
    def error(code, message, status):
        return Response({"code": code, "message": message, "request_id": None}, status=status)


class AccountListView(AccountView):
    http_method_names = ["get", "head", "post"]

    def get(self, request):
        params = request.query_params
        if set(params) - {"page", "page_size", "role", "state", "q"} or any(
            len(params.getlist(k)) != 1 for k in params
        ):
            raise ValidationError("Invalid filters.")
        queryset = (
            User.objects.select_related("profile", "invitation")
            .prefetch_related("role_assignments")
            .order_by("email", "pk")
        )
        if "role" in params:
            if params["role"] not in PlatformRole.values:
                raise ValidationError("Invalid role.")
            queryset = queryset.filter(role_assignments__role=params["role"])
        if "state" in params:
            if params["state"] not in AccountState.values:
                raise ValidationError("Invalid state.")
            queryset = queryset.filter(state=params["state"])
        if "q" in params:
            if len(params["q"]) > 100:
                raise ValidationError("Search too long.")
            query = params["q"].strip()
            queryset = queryset.filter(
                Q(email__icontains=query)
                | Q(student_id__icontains=query)
                | Q(profile__display_name__icontains=query)
            )
        for key in ("page", "page_size"):
            if key in params and (
                not params[key].isascii()
                or not params[key].isdigit()
                or len(params[key]) > 6
                or int(params[key]) < 1
            ):
                raise ValidationError("Invalid pagination.")
        paginator = Pagination()
        rows = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response([account_data(user) for user in rows])

    def post(self, request):
        data = CreateInput(data=request.data)
        data.is_valid(raise_exception=True)
        user = services.create_account(actor=request.user, **data.validated_data)
        return Response(account_data(user), status=201)


class AccountDetailView(AccountView):
    http_method_names = ["get", "head"]

    def get(self, request, pk):
        return Response(
            account_data(User.objects.select_related("profile", "invitation").get(pk=pk))
        )


class RoleView(AccountView):
    http_method_names = ["post"]

    def post(self, request, pk):
        data = RoleInput(data=request.data)
        data.is_valid(raise_exception=True)
        user = services.change_roles(actor=request.user, subject_id=pk, **data.validated_data)
        return Response(account_data(user))


class InviteView(AccountView):
    http_method_names = ["post"]

    def post(self, request, pk):
        if request.data != {}:
            raise ValidationError("No fields accepted.")
        services.resend_invitation(actor=request.user, subject_id=pk)
        return Response(
            {"message": "Invitation requested. If delivery fails, retry after the cooldown."},
            status=202,
        )


class ProfileView(AccountView):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "head", "patch"]

    def get(self, request):
        if current_principal(request.user) is None:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied()
        return Response(
            account_data(
                User.objects.select_related("profile", "invitation").get(pk=request.user.pk)
            )
        )

    def patch(self, request):
        data = ProfileInput(data=request.data)
        data.is_valid(raise_exception=True)
        user = services.update_profile(actor=request.user, **data.validated_data)
        return Response(account_data(user))


class AcceptInvitationView(AccountView):
    permission_classes = [AllowAny]
    http_method_names = ["post"]

    def post(self, request):
        data = ResetInput(data=request.data)
        data.is_valid(raise_exception=True)
        retry = consume_attempt(None, request.META.get("REMOTE_ADDR", "unknown"))
        if retry:
            response = self.error("invitation_limited", "Too many attempts. Try again later.", 429)
            response["Retry-After"] = str(retry)
            return response
        if not services.accept_invitation(**data.validated_data):
            return self.error(
                "invitation_invalid",
                "This invitation is invalid or expired. Ask your administrator for a new one.",
                400,
            )
        return Response(
            {
                "message": (
                    "Invitation accepted. Sign in once any required "
                    "administrator approval is complete."
                )
            }
        )
