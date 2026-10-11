from uuid import UUID

from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.academics.structure.api import ManageStructure, Pagination, StructureList, StructureView
from apps.access.enums import ResourceKind
from apps.access.policy import ResourceRef, allows, scope_queryset
from apps.accounts.models import User

from . import services
from .models import Offering


class OfferingPermission(BasePermission):
    def has_permission(self, request, view):
        return allows(request.user, "course.create")


def query(actor):
    return scope_queryset(
        actor,
        "course.view",
        Offering.objects.select_related("course__department", "batch", "term", "section"),
        kind=ResourceKind.OFFERING,
    )


def row_data(row):
    return {
        "id": str(row.pk),
        "name": row.name,
        "course_id": str(row.course_id),
        "course_code": row.course.code,
        "course_title": row.course.title,
        "department_label": row.course.department.label,
        "batch_id": str(row.batch_id),
        "batch_label": row.batch.label,
        "term_id": str(row.term_id),
        "term_label": row.term.label,
        "section_id": str(row.section_id),
        "section_label": row.section.label,
        "archived": row.archived,
        "revision": row.revision,
        "created_by": str(row.created_by_id),
    }


def detail(actor, row):
    return {
        **row_data(row),
        "can_manage": allows(actor, "course.manage", ResourceRef(ResourceKind.OFFERING, row.pk)),
        "can_assign": allows(actor, "system.manage"),
    }


def payload(data, mode):
    fields = {
        "create": {"course_id", "batch_id", "term_id", "section_id", "name"},
        "edit": {"name", "expected_revision"},
        "archive": {"expected_revision"},
        "assign": {"teacher_id", "expected_revision", "active"},
    }[mode]
    if not isinstance(data, dict) or set(data) != fields:
        raise ValidationError("Supply exactly the documented fields.")
    values = dict(data)
    for key, value in data.items():
        if key == "expected_revision":
            if type(value) is not int or not 1 <= value <= 2147483647:
                raise ValidationError("Invalid revision.")
        elif key == "active":
            if type(value) is not bool:
                raise ValidationError("Invalid activation.")
        elif not isinstance(value, str):
            raise ValidationError("Text is required.")
        elif key.endswith("_id"):
            try:
                values[key] = UUID(value)
            except ValueError:
                raise ValidationError("Invalid identifier.") from None
    return values


def paginate(rows, request, project):
    params = request.query_params
    if set(params) - {"page", "page_size"} or any(len(params.getlist(k)) != 1 for k in params):
        raise ValidationError("Invalid pagination.")
    for key in params:
        if (
            not params[key].isascii()
            or not params[key].isdigit()
            or len(params[key]) > 6
            or int(params[key]) < 1
        ):
            raise ValidationError("Invalid pagination.")
    paginator = Pagination()
    page = paginator.paginate_queryset(rows, request)
    return paginator.get_paginated_response([project(row) for row in page])


class OfferingView(StructureView):
    permission_classes = [OfferingPermission]

    def handle_exception(self, exc):
        response = super().handle_exception(exc)
        if response.data.get("code", "").startswith("structure_"):
            response.data["code"] = response.data["code"].replace("structure_", "offering_", 1)
            if response.status_code == 400:
                response.data["message"] = (
                    "Check the offering name, matching course/batch/term/section "
                    "and staff eligibility. "
                    "Archived records cannot receive new offerings or assignments; "
                    "duplicate offerings are not allowed."
                )
        return response

    def visible(self, pk):
        row = query(self.request.user).filter(pk=pk).first()
        if row is None:
            raise NotFound()
        return row


class OfferingList(OfferingView):
    http_method_names = ["get", "head", "post"]

    def get(self, request):
        return paginate(query(request.user), request, row_data)

    def post(self, request):
        row = services.create(actor=request.user, **payload(request.data, "create"))
        return Response(detail(request.user, row), status=201)


class OfferingDetail(OfferingView):
    http_method_names = ["get", "head", "patch"]

    def get(self, request, pk):
        return Response(detail(request.user, self.visible(pk)))

    def patch(self, request, pk):
        row = services.change(actor=request.user, pk=pk, **payload(request.data, "edit"))
        return Response(detail(request.user, row))


class OfferingArchive(OfferingView):
    http_method_names = ["post"]
    permission_classes = [ManageStructure]

    def post(self, request, pk):
        return Response(
            detail(
                request.user,
                services.change(
                    actor=request.user, pk=pk, archive=True, **payload(request.data, "archive")
                ),
            )
        )


class Teachers(OfferingView):
    http_method_names = ["get", "head", "post"]

    def get(self, request, pk):
        row = self.visible(pk)

        def project(link):
            return {
                "id": str(link.pk),
                "teacher_id": str(link.teacher_id),
                "display_name": link.teacher.profile.display_name or "Staff member",
                "assigned_at": link.assigned_at.isoformat(),
                "ended_at": link.ended_at.isoformat() if link.ended_at else None,
                "assigned_by": str(link.assigned_by_id),
                "removed_by": str(link.removed_by_id) if link.removed_by_id else None,
            }

        return paginate(
            row.teacher_assignments.select_related("teacher__profile"), request, project
        )

    def post(self, request, pk):
        # Service reauthorizes before target lookup, including for unassigned staff.
        row = services.assign(actor=request.user, pk=pk, **payload(request.data, "assign"))
        return Response(detail(request.user, row))


class StaffOptions(OfferingView):
    http_method_names = ["get", "head"]
    permission_classes = [ManageStructure]

    def get(self, request):
        rows = (
            User.objects.eligible_for_authentication()
            .filter(role_assignments__role__in=["TEACHER", "ADMINISTRATOR"])
            .select_related("profile")
            .distinct()
            .order_by("email", "pk")
        )
        return paginate(
            rows,
            request,
            lambda user: {
                "id": str(user.pk),
                "label": user.email,
                "name": user.profile.display_name or "Staff member",
            },
        )


class OfferingOptions(StructureList):
    http_method_names = ["get", "head"]
    permission_classes = [OfferingPermission]

    def queryset(self):
        rows = super().queryset().filter(archived=False)
        if self.kind == "batches":
            return rows.filter(department__archived=False)
        if self.kind in {"terms", "sections"}:
            return rows.filter(batch__archived=False, batch__department__archived=False)
        return rows
