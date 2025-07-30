from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from users.constants import NAME_MAX_LENGTH, EMAIL_MAX_LENGTH
from .validators import validate_username


def user_avatar_path(instance, filename):
    return f'avatars/{instance.username}/{filename}'


class User(AbstractUser):
    email = models.EmailField(
        'Email',
        unique=True,
        max_length=EMAIL_MAX_LENGTH,
        help_text='Адрес электронной почты'
    )
    username = models.CharField(
        max_length=NAME_MAX_LENGTH,
        unique=True,
        validators=[UnicodeUsernameValidator(), validate_username],
        error_messages={
            "unique": _(" Такой пользователь уже существует."),
        },
    )
    first_name = models.CharField(
        'Имя',
        max_length=NAME_MAX_LENGTH,
    )
    last_name = models.CharField(
        'Фамилия',
        max_length=NAME_MAX_LENGTH,
    )
    avatar = models.ImageField(
        'Аватар',
        upload_to='users',
        null=True,
        blank=True,
        help_text='Ссылка на аватар (URI)',
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', ]

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username

    def clean(self):
        if not self.email:
            raise ValidationError('Email обязателен')
        if not self.username:
            raise ValidationError('Username обязателен')


class Follow(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="follower"
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="following"
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'подписки'
        constraints = [
            models.UniqueConstraint(
                fields=["user", "following"],
                name="%(app_label)s_%(class)s_unique_relationships",
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F("following")),
                name="%(app_label)s_%(class)s_prevent_self_follow",
            ),
        ]

    def __str__(self):
        return f'{self.user.username} → {self.following.username}'
