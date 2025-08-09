from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from recipes.fields import Base64ImageField
from recipes.models import (
    Ingredient,
    Recipe,
    RecipeIngredient,
    Tag, )
from users.serializers import UserSerializer

User = get_user_model()


class TagSerializer(serializers.ModelSerializer):
    """Handles serialization and deserialization of Tag model."""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """ Serializer for writing ingredient amounts in a recipe."""
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all()
    )
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

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
    ingredients = IngredientInRecipeSerializer(
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
            'id', 'author', 'name', 'text', 'image',
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

    def _save_ingredients(self, recipe, ingredients_data):
        objs = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount']
            )
            for item in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(objs)

    @transaction.atomic
    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', [])
        tags = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self._save_ingredients(recipe, ingredients_data)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', None)
        tags = validated_data.pop('tags', None)

        instance.tags.set(tags)
        instance.ingredients.clear()
        self._save_ingredients(instance, ingredients_data)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeSerializer(
            instance,
            context=self.context
        ).data


class IngredientSerializer(serializers.ModelSerializer):
    """Serializer for Ingredient model."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Serializer for minimal recipe info in favorites and shopping cart."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class RecipeSerializer(serializers.ModelSerializer):
    """Serializer class for representing the `Recipe` model."""
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True, read_only=True, source='recipe_ingredients'
    )
    author = UserSerializer(read_only=True)
    is_favorited = serializers.BooleanField(default=False)
    is_in_shopping_cart = serializers.BooleanField(default=False)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )

    def _has_relation(self, obj, model):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and model.objects.filter(user=request.user, recipe=obj).exists()
        )
