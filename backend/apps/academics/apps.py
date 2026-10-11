from django.apps import AppConfig


class AcademicsConfig(AppConfig):
    name = "apps.academics"
    verbose_name = "Academic structure"

    def ready(self):
        from .offerings.policy import register

        register()
