from django.apps import AppConfig
from django.db.models.signals import post_migrate


class RecipesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recipes'

    def ready(self):
        import recipes.signals  # noqa: F401
