# recipes serializers.py
import base64

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import Recipe, Tag, Ingredient, RecipeIngredient, \
    Favourites, ShoppingList
from users.models import Follow
from users.serializers import UserSerializer

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            header, imgstr = data.split(';base64,')
            ext = header.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientAmountSerializer(serializers.ModelSerializer):
    # для записи: передаётся id ингредиента
    id = serializers.PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all()
    )
    # для чтения:
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField(min_value=1)

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeWriteSerializer(serializers.ModelSerializer):
    author = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )
    author_username = serializers.ReadOnlyField(source='author.username')
    # вложенные ингредиенты: и чтение, и запись
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
            'tags', 'ingredients', 'cooking_time',
        )

    def validate(self, attrs):
        """
        Проверяем, что в списке recipe_ingredients нет повторяющихся ингредиентов.
        """
        ingredients = attrs.get('recipe_ingredients', [])
        tags = attrs.get('tags', [])
        # Собираем id всех ингредиентов из входных данных
        if not ingredients:
            raise serializers.ValidationError('Ингридент объязательное поле!')
        else:
            ingredient_ids = [item['ingredient'].id for item in ingredients]

        if not tags:
            raise serializers.ValidationError({
                'tags': 'Нужно указать хотя бы один тег.'
            })
        tag_ids = [tag.id for tag in tags]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError({
                'tags': 'Теги должны быть уникальными в одном рецепте.'
            })
        # Если длина списка не совпадает с длиной множества - есть дубли
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                "Ингредиенты должны быть уникальными в рамках одного рецепта."
            )
        return attrs

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', [])
        tags_data = validated_data.pop('tags', [])
        author = validated_data.pop('author')
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.tags.set(tags_data)

        for item in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount']
            )
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', None)
        tags_data = validated_data.pop('tags', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tags_data is not None:
            instance.tags.set(tags_data)

        if ingredients_data is not None:
            instance.recipe_ingredients.all().delete()
            for item in ingredients_data:
                RecipeIngredient.objects.create(
                    recipe=instance,
                    ingredient=item['ingredient'],
                    amount=item['amount']
                )
        return instance


class RecipeDetailSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True, read_only=True,
        source='recipe_ingredients'
    )
    author = UserSerializer(read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time',
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

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False

        return Follow.objects.filter(
            user=request.user, following=obj.author
        ).exists()


class RecipeListSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True,
        read_only=True,
        source='recipe_ingredients'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time',
        )

    def is_favorited(self, obj):
        user = self.context['request'].user
        return not user.is_anonymous and Favourites.objects.filter(user=user, recipe=obj).exists()

    def is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return not user.is_anonymous and ShoppingList.objects.filter(user=user, recipe=obj).exists()



class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class FavouritesSerializer(serializers.ModelSerializer):

    class Meta:
        model = Favourites
        fields = ('user', 'recipe')


    def validate(self, data):
        user = data.get('user')
        recipe = data.get('recipe')
        if Favourites.objects.filter(user=user, recipe=recipe).exists():
            raise ValidationError(f'Рецепт {recipe} уже добавлен в избранное!')
        return data


class ShoppingListSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.all()
    )
    images = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    cooking_time = serializers.SerializerMethodField()

    class Meta:
        model = ShoppingList
        fields = ('user', 'recipe', 'name', 'images', 'cooking_time')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
