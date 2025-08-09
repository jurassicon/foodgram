from django.apps import AppConfig
from django.db.models.signals import post_migrate
from social_core.utils import first


class RecipesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recipes'
