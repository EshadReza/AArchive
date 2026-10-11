from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.access.policy import allows
from apps.accounts.auth.views import AuthView

from . import services


class ManageStructure(BasePermission):
    def has_permission(self, request, view):
        return allows(request.user, "system.manage")


def project(kind, row):
    parent = services.PARENTS.get(kind)
    data = {
        "id": str(row.pk),
        "label": row.label,
        "name": row.name,
        "archived": row.archived,
        "revision": row.revision,
    }
    if parent:
        data[f"{parent[0]}_id"] = str(getattr(row, f"{parent[0]}_id"))
        parent_row = getattr(row, parent[0])
        data["parent_label"] = (
            f"{parent_row.department.label} / {parent_row.label}"
            if isinstance(parent_row, services.Batch)
            else parent_row.label
        )
    try:
        services.require_active(row)
        data["available"] = True
    except DjangoValidationError:
        data["available"] = False
    return data


def payload(data, kind, operation):
    fields = {"expected_revision"} if operation == "archive" else {"label", "name"}
    if operation == "edit":
        fields.add("expected_revision")
    if operation == "create" and kind in services.PARENTS:
        fields.add(f"{services.PARENTS[kind][0]}_id")
    if not isinstance(data, dict) or set(data) != fields:
        raise ValidationError("Supply exactly the documented fields.")
    result = {}
    for key, value in data.items():
        if key == "expected_revision":
            if type(value) is not int or not 1 <= value <= 2147483647:
                raise ValidationError("Invalid revision.")
        elif key.endswith("_id"):
            if not isinstance(value, str):
                raise ValidationError("Invalid parent.")
            try:
                value = UUID(value)
            except ValueError:
                raise ValidationError("Invalid parent.") from None
            key = "parent_id"
        elif not isinstance(value, str):
            raise ValidationError("Text is required.")
        result[key] = value
    return result


class Pagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


@method_decorator(csrf_protect, name="dispatch")
class StructureView(AuthView):
    permission_classes = [ManageStructure]
    kind = None

    def handle_exception(self, exc):
        status, code, message = (
            400,
            "structure_invalid",
            "Check the label, name and parent. Labels must be unique within their parent; "
            "archived structure cannot receive new assignments or edits.",
        )
        if isinstance(exc, services.StructureConflict):
            status, code, message = (
                409,
                "structure_conflict",
                "This record changed. Reload and review again.",
            )
        elif isinstance(exc, ObjectDoesNotExist):
            exc = NotFound()
        elif isinstance(exc, IntegrityError):
            status, code, message = (
                409,
                "structure_conflict",
                "This change conflicts with an existing record or protected relationship.",
            )
        elif not isinstance(exc, DjangoValidationError | serializers.ValidationError):
            return super().handle_exception(exc)
        if isinstance(exc, NotFound):
            return super().handle_exception(exc)
        return Response({"code": code, "message": message, "request_id": None}, status=status)

    def queryset(self):
        queryset = services.MODELS[self.kind].objects.all()
        if self.kind == "batches":
            queryset = queryset.select_related("department")
        elif self.kind in {"terms", "sections"}:
            queryset = queryset.select_related("batch__department")
        return queryset


class StructureList(StructureView):
    http_method_names = ["get", "head", "post"]

    def get(self, request):
        params = request.query_params
        parent = services.PARENTS.get(self.kind)
        parent_key = f"{parent[0]}_id" if parent else None
        allowed = {"page", "page_size", "archived"} | ({parent_key} if parent else set())
        if set(params) - allowed or any(len(params.getlist(k)) != 1 for k in params):
            raise ValidationError("Invalid filters.")
        queryset = self.queryset()
        for key in ("page", "page_size"):
            if key in params and (
                not params[key].isascii()
                or not params[key].isdigit()
                or len(params[key]) > 6
                or int(params[key]) < 1
            ):
                raise ValidationError("Invalid pagination.")
        if "archived" in params:
            if params["archived"] not in {"true", "false"}:
                raise ValidationError("Invalid archive filter.")
            queryset = queryset.filter(archived=params["archived"] == "true")
        if parent_key and parent_key in params:
            try:
                parent_id = UUID(params[parent_key])
            except ValueError:
                raise ValidationError("Invalid parent.") from None
            queryset = queryset.filter(**{parent_key: parent_id})
        pagination = Pagination()
        rows = pagination.paginate_queryset(queryset, request, view=self)
        return pagination.get_paginated_response([project(self.kind, row) for row in rows])

    def post(self, request):
        row = services.create(
            actor=request.user, kind=self.kind, **payload(request.data, self.kind, "create")
        )
        return Response(project(self.kind, row), status=201)


class StructureDetail(StructureView):
    http_method_names = ["get", "head", "patch"]

    def get(self, request, pk):
        return Response(project(self.kind, self.queryset().get(pk=pk)))

    def patch(self, request, pk):
        row = services.change(
            actor=request.user, kind=self.kind, pk=pk, **payload(request.data, self.kind, "edit")
        )
        return Response(project(self.kind, row))


class StructureArchive(StructureView):
    http_method_names = ["post"]

    def post(self, request, pk):
        row = services.change(
            actor=request.user,
            kind=self.kind,
            pk=pk,
            archive=True,
            **payload(request.data, self.kind, "archive"),
        )
        return Response(project(self.kind, row))
