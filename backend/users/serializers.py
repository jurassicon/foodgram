from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework_simplejwt.tokens import AccessToken

from users.validators import validate_username
from .constants import CODE_MAX_LENGTH, EMAIL_MAX_LENGTH, NAME_MAX_LENGTH
from .models import User
from .utils import send_email_code


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        fields = (
            'username', 'email', 'first_name',
            'last_name', 'avatar',
        )
        model = User


class UserRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=NAME_MAX_LENGTH,
                                     validators=[UnicodeUsernameValidator(),
                                                 validate_username], )
    email = serializers.EmailField(
        max_length=EMAIL_MAX_LENGTH,
    )

    def create(self, validated_data):
        username = validated_data.get('username')
        email = validated_data.get('email')
        try:
            user, created = User.objects.get_or_create(username=username,
                                                       email=email)
        except IntegrityError:
            raise serializers.ValidationError(
                f'Пользователь с {username} занят')
        send_email_code(user)
        return user


class ConfirmationCodeTokenSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=NAME_MAX_LENGTH,
        write_only=True
    )
    confirmation_code = serializers.CharField(
        max_length=CODE_MAX_LENGTH,
        write_only=True
    )

    def validate(self, data):
        user = get_object_or_404(User, username=data['username'])
        if user.confirmation_code != data['confirmation_code']:
            raise serializers.ValidationError(
                'Неверный код подтверждения'
            )
        token = str(AccessToken.for_user(user))
        return {'token': token}
