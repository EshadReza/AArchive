from uuid import UUID

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.academics.structure.api import Pagination, StructureView
from apps.access.policy import allows, current_principal

from . import services


class CatalogPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method not in {"GET", "HEAD"}:
            return allows(request.user, "system.manage")
        principal = current_principal(request.user)
        return principal is not None and bool(principal.roles & {"ADMINISTRATOR", "TEACHER"})


def project(row):
    return {
        "id": str(row.pk),
        "department_id": str(row.department_id),
        "department_label": row.department.label,
        "department_name": row.department.name,
        "code": row.code,
        "title": row.title,
        "credits": format(row.credits, ".2f"),
        "description": row.description,
        "archived": row.archived,
        "available": not row.archived and not row.department.archived,
        "revision": row.revision,
    }


def payload(data, operation):
    fields = (
        {"expected_revision"}
        if operation == "archive"
        else {"code", "title", "credits", "description"}
    )
    if operation == "create":
        fields.add("department_id")
    elif operation == "edit":
        fields.add("expected_revision")
    if not isinstance(data, dict) or set(data) != fields:
        raise ValidationError("Supply exactly the documented fields.")
    result = dict(data)
    for key, value in data.items():
        if key == "expected_revision":
            if type(value) is not int or not 1 <= value <= 2147483647:
                raise ValidationError("Invalid revision.")
        elif not isinstance(value, str):
            raise ValidationError("Text values are required, including credits.")
    if "department_id" in result:
        try:
            result["department_id"] = UUID(result["department_id"])
        except ValueError:
            raise ValidationError("Invalid department.") from None
    return result


class CourseView(StructureView):
    permission_classes = [CatalogPermission]

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        code = response.data.get("code", "")
        if code.startswith("structure_"):
            response.data["code"] = code.replace("structure_", "course_", 1)
            if response.status_code == 400:
                response.data["message"] = (
                    "Check course fields and department. "
                    "Codes must be unique within the department; "
                    "credits must be text from 0 to 99.99 with at most two decimal places. "
                    "Archived courses or departments cannot receive edits or new courses."
                )
        return response

    def queryset(self):
        return services.catalog(self.request.user)


class CourseList(CourseView):
    http_method_names = ["get", "head", "post"]

    def get(self, request):
        params = request.query_params
        if set(params) - {"page", "page_size", "department_id", "archived", "q"} or any(
            len(params.getlist(k)) != 1 for k in params
        ):
            raise ValidationError("Invalid filters.")
        rows = self.queryset()
        for key in ("page", "page_size"):
            if key in params and (
                not params[key].isascii()
                or not params[key].isdigit()
                or len(params[key]) > 6
                or int(params[key]) < 1
            ):
                raise ValidationError("Invalid pagination.")
        if "department_id" in params:
            try:
                rows = rows.filter(department_id=UUID(params["department_id"]))
            except ValueError:
                raise ValidationError("Invalid department.") from None
        if "archived" in params:
            if params["archived"] not in {"true", "false"}:
                raise ValidationError("Invalid archive filter.")
            rows = rows.filter(archived=params["archived"] == "true")
        if "q" in params:
            from django.db.models import Q

            if len(params["q"]) > 100:
                raise ValidationError("Search too long.")
            query = params["q"].strip()
            rows = rows.filter(Q(code__icontains=query) | Q(title__icontains=query))
        paginator = Pagination()
        page = paginator.paginate_queryset(rows, request, view=self)
        return paginator.get_paginated_response([project(row) for row in page])

    def post(self, request):
        row = services.create(actor=request.user, **payload(request.data, "create"))
        return Response(project(row), status=201)


class CourseDetail(CourseView):
    http_method_names = ["get", "head", "patch"]

    def get(self, request, pk):
        return Response(project(self.queryset().get(pk=pk)))

    def patch(self, request, pk):
        row = services.change(actor=request.user, pk=pk, **payload(request.data, "edit"))
        return Response(project(row))


class CourseArchive(CourseView):
    http_method_names = ["post"]

    def post(self, request, pk):
        row = services.change(
            actor=request.user, pk=pk, archive=True, **payload(request.data, "archive")
        )
        return Response(project(row))
