from django.apps import AppConfig
from django.db.models import Q


class AccessConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.access"

    def ready(self):
        from apps.accounts.enums import PlatformRole
        from apps.audit.models import AuditLog

        from .enums import ResourceKind
        from .policy import ResourcePolicy, register_policy

        register_policy(
            ResourceKind.AUDIT,
            ResourcePolicy(
                AuditLog,
                {
                    "audit.view": lambda principal: (
                        Q() if PlatformRole.ADMINISTRATOR in principal.roles else Q(pk__in=[])
                    ),
                },
            ),
        )
