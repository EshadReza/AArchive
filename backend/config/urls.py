from django.urls import path

from apps.academics.structure.api import StructureArchive, StructureDetail, StructureList
from apps.accounts.api.views import (
    AcceptInvitationView,
    AccountDetailView,
    AccountListView,
    InviteView,
    ProfileView,
    RoleView,
)
from apps.accounts.auth.views import LoginView, LogoutView, SessionView
from apps.accounts.recovery.views import (
    ChangePasswordView,
    LifecycleView,
    ResetConfirmView,
    ResetRequestView,
)
from apps.accounts.registration.views import RegistrationView, ResendView, VerifyView
from apps.audit.api import AuditDetailView, AuditListView

from .health import HealthView

urlpatterns = [
    path("api/users", AccountListView.as_view()),
    path("api/users/<uuid:pk>", AccountDetailView.as_view()),
    path("api/users/<uuid:pk>/roles", RoleView.as_view()),
    path("api/users/<uuid:pk>/invitation", InviteView.as_view()),
    path("api/profile", ProfileView.as_view()),
    path("api/auth/invitation/accept", AcceptInvitationView.as_view()),
    path("api/auth/password-reset", ResetRequestView.as_view(), name="password-reset"),
    path(
        "api/auth/password-reset/confirm", ResetConfirmView.as_view(), name="password-reset-confirm"
    ),
    path("api/auth/password-change", ChangePasswordView.as_view(), name="password-change"),
    path("api/users/<uuid:pk>/lifecycle", LifecycleView.as_view(), name="account-lifecycle"),
    path("api/auth/register", RegistrationView.as_view(), name="auth-register"),
    path("api/auth/verify", VerifyView.as_view(), name="auth-verify"),
    path("api/auth/resend-verification", ResendView.as_view(), name="auth-resend"),
    path("api/auth/session", SessionView.as_view(), name="auth-session"),
    path("api/auth/login", LoginView.as_view(), name="auth-login"),
    path("api/auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("api/health", HealthView.as_view(), name="health"),
    path("api/audit", AuditListView.as_view(), name="audit-list"),
    path("api/audit/<int:pk>", AuditDetailView.as_view(), name="audit-detail"),
]

for kind in ("departments", "batches", "terms", "sections"):
    urlpatterns.extend(
        [
            path(f"api/{kind}", StructureList.as_view(kind=kind)),
            path(f"api/{kind}/<uuid:pk>", StructureDetail.as_view(kind=kind)),
            path(f"api/{kind}/<uuid:pk>/archive", StructureArchive.as_view(kind=kind)),
        ]
    )
