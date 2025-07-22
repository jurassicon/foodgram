# recipes serializers.py
from recipes.models import Recipe, Tag, Ingredient, RecipeIngredient
from rest_framework import serializers


class IngredientAmountSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):

    ingredients = IngredientAmountSerializer(
        many=True,
        source='recipe_ingredients',
        # ← общее имя related_name в модели RecipeIngredient
        read_only=True
    )

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'text', 'image',
                  'tags', 'ingredients', 'cooking_time')

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients_data = validated_data.pop('ingredients')
        # задаём автора:
        user = self.context['request'].user
        recipe = Recipe.objects.create(author=user, **validated_data)
        # связываем теги
        recipe.tags.set(tags)
        # создаём связь через through-модель
        for ing in ingredients_data:
            RecipeIngredient.objects.create(
                recipe=recipe,
                ingredient_id=ing['id'],
                amount=ing['amount']
            )
        return recipe


class RecipeDetailSerializer(serializers.ModelSerializer):

    ingredients = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name'
    )
    tags = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field='name'
    )
    author = serializers.SlugRelatedField(
        read_only=True, slug_field='username'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request is None:
            return False
        return obj.is_favorited(request.user)

    def get_is_in_shopping_cart(self, obj):
        request = self.context.get('request')
        if request is None:
            return False
        return obj.is_in_shopping_cart(request.user)
    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request is None:
            return False
        return obj.is_subscribed(request.user)
    class Meta:
        fields = (
            'author', 'ingredients', 'tags', 'image',
            'name', 'text', 'cooking_time',
            'is_favorited', 'is_in_shopping_cart', 'is_subscribed'
        )
        model = Recipe


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        fields = ('id', 'name', 'slug')
        model = Tag

