from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework_simplejwt.tokens import AccessToken
from drf_extra_fields.fields import Base64ImageField
from users.validators import validate_username
from .constants import CODE_MAX_LENGTH, EMAIL_MAX_LENGTH, NAME_MAX_LENGTH
from .models import User
from .utils import send_email_code


User = get_user_model()


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username','email','first_name','last_name','avatar')
        read_only_fields = ('username','email')


class UserRegistrationSerializer(serializers.Serializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )

    username = serializers.CharField(max_length=NAME_MAX_LENGTH,
                                     validators=[UnicodeUsernameValidator(),
                                                 validate_username], )
    email = serializers.EmailField(
        max_length=EMAIL_MAX_LENGTH,
    )
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'password')

    def create(self, validated_data):
        password = validated_data.pop('password')
        # создаём экземпляр, не сохраняя пока в БД
        user = User(**validated_data)
        user.set_password(password)
        try:
            user.save()
        except IntegrityError:
            # ловим нарушение unique=True на username или email
            raise serializers.ValidationError({
                'username': f'Пользователь с именем "{validated_data.get("username")}" уже существует.',
                'email':    f'Email "{validated_data.get("email")}" уже занят.',
            })
        return user
