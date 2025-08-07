from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers

from recipes.models import Recipe
from users.models import Follow, User


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
        return bool(
            request and request.user.is_authenticated
            and Follow.objects.filter(
                user=request.user, following=obj
            ).exists()
        )


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


class UserWithRecipesSerializer(UserSerializer):
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

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + (
            'recipes',
            'recipes_count',
        )

    def get_recipes(self, obj):
        qs = Recipe.objects.filter(author=obj).order_by('-pub_date')
        limit = self.context['request'].query_params.get('recipes_limit')
        if limit is not None and limit.isdigit():
            qs = qs[:int(limit)]
        return RecipeMinifiedSerializer(
            qs, many=True, context=self.context
        ).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()
