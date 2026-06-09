from django.apps import AppConfig


class BaseAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Base_App'

    def ready(self):
        import Base_App.signals  # noqa: F401

