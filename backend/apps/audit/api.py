from django.core.exceptions import ValidationError
from rest_framework import generics, permissions, serializers
from rest_framework.exceptions import NotFound
from rest_framework.pagination import CursorPagination

from apps.access.enums import ResourceKind
from apps.access.policy import allows, scope_queryset

from .models import AuditLog
from .policy import project_payload


class CanReadAudit(permissions.BasePermission):
    def has_permission(self, request, view):
        return allows(request.user, "audit.view")


class AuditSerializer(serializers.ModelSerializer):
    actor_id = serializers.UUIDField(read_only=True, allow_null=True)
    previous_value = serializers.SerializerMethodField()
    new_value = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor_id",
            "system_actor",
            "action",
            "target_type",
            "target_id",
            "previous_value",
            "new_value",
            "reason",
            "request_id",
            "ip",
            "channel",
            "created_at",
        )
        read_only_fields = fields

    def safe_value(self, obj, value):
        try:
            return project_payload(obj.action, value)
        except ValidationError:
            # Fail closed for malformed legacy/manual data; never echo raw values.
            return None

    def get_previous_value(self, obj):
        return self.safe_value(obj, obj.previous_value)

    def get_new_value(self, obj):
        return self.safe_value(obj, obj.new_value)


class AuditPagination(CursorPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-id"

    def decode_cursor(self, request):
        if len(request.query_params.get(self.cursor_query_param, "")) > 1024:
            raise NotFound(self.invalid_cursor_message)
        cursor = super().decode_cursor(request)
        if cursor is not None and cursor.position is not None:
            position = cursor.position
            if (
                len(position) > 19
                or not position.isascii()
                or not position.isdecimal()
                or not 0 < int(position) <= 9223372036854775807
            ):
                raise NotFound(self.invalid_cursor_message)
        return cursor


class AuditReadMixin:
    permission_classes = [CanReadAudit]
    serializer_class = AuditSerializer
    queryset = AuditLog.objects.all()
    http_method_names = ["get", "head"]

    def get_queryset(self):
        return scope_queryset(
            self.request.user, "audit.view", super().get_queryset(), kind=ResourceKind.AUDIT
        )

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        codes = {
            400: "invalid_request",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
        }
        response.data = {
            "code": codes.get(response.status_code, "request_failed"),
            "message": str(response.data.get("detail", "Request failed.")),
            "request_id": None,
        }
        return response

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class AuditListView(AuditReadMixin, generics.ListAPIView):
    pagination_class = AuditPagination


class AuditDetailView(AuditReadMixin, generics.RetrieveAPIView):
    pass
