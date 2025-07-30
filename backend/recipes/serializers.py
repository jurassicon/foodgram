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
    """A custom serializer field for handling base64-encoded images."""

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            header, imgstr = data.split(';base64,')
            ext = header.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'temp.{ext}')
        return super().to_internal_value(data)


class TagSerializer(serializers.ModelSerializer):
    """
    Handles the serialization and deserialization of Tag model data.

    This serializer is designed to validate and transform data pertaining
    to the Tag model between native Python objects and JSON, and vice versa.
    It ensures that the fields `id`, `name`, and `slug` are correctly handled,
    making it useful for APIs working with the Tag model.
    """

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientAmountSerializer(serializers.ModelSerializer):
    """
    Serializer for handling ingredient amounts within a recipe.

    This serializer is responsible for managing the data representation for
    ingredient amounts within a recipe, including validation and field
    mappings. It allows for linking ingredients to a recipe using their primary
    key and accessing related information such as name, measurement unit,
    and amount. It enforces business rules, such as the minimum value for the
    amount field.
    """
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
    """
    Serializer for representing ingredients in a recipe.

    This class is designed to serialize and deserialize data related to
    ingredients that are part of a recipe. It provides a read-only
    representation of certain fields from a related ingredient model, while
    allowing modification of the ingredient's quantity.
    """
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeWriteSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating Recipe objects.

    This serializer provides validation and data handling for creating and
    updating recipes, including nested relationships such as ingredients and tags.
    It ensures that ingredients and tags are unique within the same recipe and
    handles specific business logic during creation and update.
    """
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
    """
    Serializer for detailed representation of a Recipe model.

    This serializer provides additional information about the tags,
    ingredients, and author of the recipe. It also includes metadata about
    whether a recipe is marked as favorited or included in the shopping cart
    for the authenticated user.
    """
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
    """
    Serializer for the Recipe model, designed to format and validate recipe
    data in conformity with API requirements.

    Provides fields for recipe details, including associated tags, author,
    ingredients, and metadata for user-specific details like favorited status
    and inclusion in the shopping cart. Facilitates representation of nested
    relationships via other serializers.
    """
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

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return not user.is_anonymous and Favourites.objects.filter(
            user=user, recipe=obj
        ).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return not user.is_anonymous and ShoppingList.objects.filter(
            user=user, recipe=obj
        ).exists()


class IngredientSerializer(serializers.ModelSerializer):
    """
    Handles the serialization of Ingredient model instances.

    This serializer maps data between Ingredient model instances and their
    representational format such as JSON. It is primarily used for
    serializing and deserializing data to and from API endpoints.
    """

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class FavouritesSerializer(serializers.ModelSerializer):
    """
    Serializer for managing the Favourites model used to handle the user's
    favourite recipes.

    Provides validation to ensure that the same user cannot add the same
    recipe to their favourites multiple times. This serializer is based
    on the Favourites model and includes the fields 'user' and 'recipe'.
    """

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
    """
    Serializes data for the ShoppingList model.

    This serializer is used to define how instances of the ShoppingList model
     are converted to and from representations such as JSON. It includes fields
    such asn user, recipe, name, images, and cooking_time. For the `user`
    field, it utilizes the `CurrentUserDefault` to automatically set the
    current user, while the `recipe` field uses a `PrimaryKeyRelatedField`
    to reference Recipe objects.
    """
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
