from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import IntegrityError
from drf_extra_fields.fields import Base64ImageField
from recipes.models import Recipe
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from users.validators import validate_username

from .constants import EMAIL_MAX_LENGTH, NAME_MAX_LENGTH
from .models import Follow, User


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('avatar',)

    def validate(self, data):
        if 'avatar' not in data:
            raise serializers.ValidationError('Поле avatar обязательно!')
        return data


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user model."""
    avatar = serializers.ImageField(read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('username', 'id', 'email', 'first_name', 'last_name',
                  'is_subscribed', 'avatar',)
        read_only_fields = ('username', 'email')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Follow.objects.filter(
            user=request.user,
            following=obj
        ).exists()


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    id = serializers.IntegerField(read_only=True)
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )

    username = serializers.CharField(
        max_length=NAME_MAX_LENGTH,
        validators=[UnicodeUsernameValidator(), validate_username],
        required=True,
        allow_blank=False,
    )
    email = serializers.EmailField(
        max_length=EMAIL_MAX_LENGTH,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="Пользователь с таким email уже зарегистрирован."
            )
        ],
        required=True,
        allow_blank=False,
    )
    first_name = serializers.CharField(
        required=True, allow_blank=False, max_length=NAME_MAX_LENGTH
    )
    last_name = serializers.CharField(
        required=True, allow_blank=False, max_length=NAME_MAX_LENGTH
    )

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name',
                  'password')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        try:
            user.save()
        except IntegrityError:
            raise serializers.ValidationError({
                'username': f'Пользователь с именем '
                f'"{validated_data.get("username")}" уже существует.',
                'email': f'Email "{validated_data.get("email")}" уже занят.',
            })
        return user


class UserListSerializer(serializers.ModelSerializer):
    """Serializer for listing users."""
    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name', 'last_name')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Serializer for minimal recipe info in favorites and shopping cart."""
    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class UserWithRecipesSerializer(serializers.ModelSerializer):
    """
    Serializer for a user with additional fields related to their recipes and
    subscription status.

    This serializer extends a standard model serializer, adding computed fields
    for recipes, the count of recipes, and subscription status to another user.
    These fields provide additional insights into the user's activity and
    relationships.
    """
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'avatar',
            'is_subscribed',
            'recipes',
            'recipes_count',
        )
        read_only_fields = fields

    def get_is_subscribed(self, obj):
        """
        Возвращает, подписан ли текущий request.user на этого obj.
        """
        user = self.context['request'].user
        if not user.is_authenticated:
            return False
        return Follow.objects.filter(user=user, following=obj).exists()

    def get_recipes(self, obj):
        qs = Recipe.objects.filter(author=obj).order_by('-pub_date')
        # recipes_limit передаётся в query params
        limit = self.context['request'].query_params.get('recipes_limit')
        if limit is not None and limit.isdigit():
            qs = qs[:int(limit)]
        return RecipeMinifiedSerializer(qs, many=True,
                                        context=self.context).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()
