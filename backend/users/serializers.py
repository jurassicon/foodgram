from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import IntegrityError
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import Recipe
from users.validators import validate_username
from .constants import EMAIL_MAX_LENGTH, NAME_MAX_LENGTH
from .models import User, Follow

User = get_user_model()


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
    avatar = serializers.ImageField(read_only=True)
    is_subscribed = serializers.SerializerMethodField()
    subscriptions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('username', 'id', 'email', 'first_name', 'last_name',
                  'is_subscribed', 'avatar', 'subscriptions')
        read_only_fields = ('username', 'email')

    def get_subscriptions(self, obj):
        # на кого подписан пользователь obj
        follows = Follow.objects.filter(user=obj) \
            .values_list('following', flat=True)
        users = User.objects.filter(pk__in=follows)
        # вложенный сериализатор (только базовые поля, без рекурсии)
        return UserSerializer(users, many=True,
                              context=self.context).data

    def get_is_subscribed(self, obj):
        """
        Вернёт True, если текущий пользователь (из context) подписан на пользователя obj.
        """
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Follow.objects.filter(
            user=request.user,
            following=obj
        ).exists()


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
                'email': f'Email "{validated_data.get("email")}" уже занят.',
            })
        return user

class RecipeMinifiedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time',
        )


class UserWithRecipesSerializer(serializers.ModelSerializer):
    # досигает UserWithRecipes из OpenAPI: сюда попадают рецепты
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
        """
        Возвращает список рецептов автора obj,
        обрезанный по параметру recipes_limit.
        """
        qs = Recipe.objects.filter(author=obj).order_by('-pub_date')
        # recipes_limit передаётся в query params
        limit = self.context['request'].query_params.get('recipes_limit')
        if limit is not None and limit.isdigit():
            qs = qs[:int(limit)]
        # Minified-сериализатор отдаёт только id, name, image, cooking_time
        return RecipeMinifiedSerializer(qs, many=True, context=self.context).data

    def get_recipes_count(self, obj):
        """
        Общее число рецептов автора obj.
        """
        return Recipe.objects.filter(author=obj).count()