import base64

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers
from users.serializers import UserSerializer

from recipes.models import (Favourites, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, Tag)

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """A custom serializer field for handling base64-encoded images. """
    def to_internal_value(self, data):
        if self._is_base64(data):
            data = self._decode_base64(data)
        return super().to_internal_value(data)

    def _is_base64(self, data):
        return isinstance(data, str) and data.startswith('data:image')

    def _decode_base64(self, data):
        header, imgstr = data.split(';base64,')
        ext = header.split('/')[-1]
        return ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')


class TagSerializer(serializers.ModelSerializer):
    """Handles serialization and deserialization of Tag model."""
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientAmountSerializer(serializers.ModelSerializer):
    """ Serializer for writing ingredient amounts in a recipe."""
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all()
    )
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """Serializer for reading ingredients in a recipe. """
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeWriteSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating Recipe objects with nested tags and
    ingredients.
    """

    author = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )
    author_username = serializers.ReadOnlyField(source='author.username')
    ingredients = IngredientAmountSerializer(
        many=True,
        source='recipe_ingredients'
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all()
    )
    image = Base64ImageField(use_url=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'name', 'author_username', 'text', 'image',
            'tags', 'ingredients', 'cooking_time'
        )

    def validate(self, attrs):
        ingredients = attrs.get('recipe_ingredients', [])
        tags = attrs.get('tags', [])
        if not ingredients:
            raise serializers.ValidationError('Ингридент объязательное поле!')
        ingredient_ids = [item['ingredient'].id for item in ingredients]
        if not tags:
            raise serializers.ValidationError(
                {'tags': 'Нужно указать хотя бы один тег.'})
        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError(
                {'tags': 'Теги должны быть уникальными в одном рецепте.'})
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты должны быть уникальными в рамках одного рецепта.'
            )
        return attrs

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', [])
        tags = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        for item in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', None)
        tags = validated_data.pop('tags', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            for item in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=item['ingredient'],
                    amount=item['amount']
                )
        return instance


class IngredientSerializer(serializers.ModelSerializer):
    """Serializer for Ingredient model."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class FavouritesSerializer(serializers.ModelSerializer):
    """Serializer for managing favorites."""
    class Meta:
        model = Favourites
        fields = ('user', 'recipe')

    def validate(self, data):
        user = data.get('user')
        recipe = data.get('recipe')
        if Favourites.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError(
                f'Рецепт {recipe} уже добавлен в избранное!'
            )
        return data


class ShoppingListSerializer(serializers.ModelSerializer):
    """Serializer for shopping list entries."""
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all())
    name = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    cooking_time = serializers.SerializerMethodField()

    class Meta:
        model = ShoppingList
        fields = ('user', 'recipe', 'name', 'images', 'cooking_time')

    def get_name(self, obj):
        return obj.recipe.name

    def get_images(self, obj):
        return obj.recipe.image.url

    def get_cooking_time(self, obj):
        return obj.recipe.cooking_time


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Serializer for minimal recipe info in favorites and shopping cart."""
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class BaseRecipeSerializer(serializers.ModelSerializer):
    """Base serializer for Recipe model."""
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True, read_only=True, source='recipe_ingredients'
    )
    author = UserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return Favourites.objects.filter(
            user=request.user, recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return ShoppingList.objects.filter(
            user=request.user, recipe=obj
        ).exists()
