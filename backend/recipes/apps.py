from django.apps import AppConfig
from django.db.models.signals import post_migrate


class RecipesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recipes'

    # !!! Удалить перед продом!!!
    def ready(self):
        from django.contrib.auth import get_user_model

        def create_admin(sender, **kwargs):
            User = get_user_model()
            username = 'cherkasov'
            email = 'admin@example.com'
            password = 'JURAssic'

            # либо найдём, либо создадим пользователя
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email}
            )
            if created:
                # если только что создали — сделаем его суперюзером
                user.set_password(password)
                user.is_staff = True
                user.is_superuser = True
                user.save()

        post_migrate.connect(create_admin, sender=self)
