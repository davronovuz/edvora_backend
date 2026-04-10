from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.billing'
    verbose_name = "Billing (Moliya tizimi)"

    def ready(self):
        import apps.billing.signals  # noqa: F401
