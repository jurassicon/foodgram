import django_filters
from django.contrib.auth import get_user_model
from django_filters import rest_framework as filters

from recipes.models import Ingredient, ShoppingList
from recipes.models import Recipe, Tag

User = get_user_model()


class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='istartswith'
    )

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(filters.FilterSet):
    tags = filters.ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug'
    )
    is_favorited = filters.BooleanFilter(method='filter_in_shopping_list')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_in_shopping_list'
    )
    ingredient_name = filters.CharFilter(
        field_name='ingredients__name',
        lookup_expr='istartswith'
    )

    class Meta:
        model = Recipe
        fields = ('tags', 'author', 'is_favorited',
                  'is_in_shopping_cart', 'ingredient_name')

    def filter_is_favorited(self, queryset, name, value):
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favorites__user=user)
        return queryset

    def filter_in_shopping_list(self, queryset, name, value):
        # если не нужно фильтровать — отдаём всё
        if not value:
            return queryset

        user = self.request.user
        # если не авторизован — по логике можешь вернуть пусто или все,
        # здесь выбираю пусто, чтобы было очевидно
        if not user.is_authenticated:
            return queryset.none()

        # получаем все recipe_id, что в списке покупок у текущего пользователя
        recipe_ids = ShoppingList.objects.filter(
            user=user
        ).values_list('recipe_id', flat=True)

        # DEBUG: чтобы увидеть в консоли, что именно мы отфильтровали,
        # можешь временно раскомментировать:
        # print('shopping_cart filter, user=', user, 'ids=', list(recipe_ids))

        # и отфильтровываем
        return queryset.filter(id__in=recipe_ids)
