from django.contrib.auth import get_user_model
from django.db.models import Sum, F
from django.http import HttpResponse
from django.shortcuts import redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated, \
    IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from api.filters import RecipeFilter, IngredientFilter
from api.permissions import IsAuthorOrReadOnly
from recipes.models import Ingredient, Recipe, Tag, RecipeIngredient, \
    ShoppingList, Favourites
from recipes.pagination import CustomUserPagination
from recipes.serializers import IngredientSerializer, \
    TagSerializer, RecipeWriteSerializer, \
    RecipeDetailSerializer, RecipeListSerializer, RecipeMinifiedSerializer

User = get_user_model()


class RecipeViewSet(viewsets.ModelViewSet):
    """
    A view set for managing recipes in the system.

    This view set provides functionality for creating, retrieving, updating,
    and deleting recipes, as well as custom actions such as adding/removing
    recipes from a shopping cart, downloading a shopping list, retrieving
    a short link for a recipe, and managing favorite recipes. It supports
    different serializers depending on the action, allows fine-grained
    permission control, and integrates with custom filtering, pagination,
    and backend configurations.

    :ivar permission_classes: Specifies the permissions required to access
                              the view. By default, it ensures that the
                              resource can be accessed either by an
                              authenticated user or in a read-only manner.
    :type permission_classes: list
    :ivar queryset: The set of recipes that this view will interact with.
                    Recipes are ordered by their unique ID.
    :type queryset: QuerySet
    :ivar pagination_class: Specifies the pagination class to be used for
                             paginating the recipes.
    :type pagination_class: type
    :ivar filterset_class: Specifies the filtering class used to filter
                           recipes according to custom rules.
    :type filterset_class: type
    :ivar filter_backends: Specifies the filtering backend(s) to be used
                           by the view for advanced filtering.
    :type filter_backends: list
    """

    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    queryset = Recipe.objects.all().order_by('id')
    pagination_class = CustomUserPagination
    filterset_class = RecipeFilter
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeWriteSerializer
        if self.action == 'list':
            return RecipeListSerializer
        return RecipeDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        recipe = self.get_object()
        detail_ser = RecipeDetailSerializer(
            recipe,
            context=self.get_serializer_context()
        )
        response.data = detail_ser.data
        return response

    partial_update = update

    @action(
        detail=True,
        methods=['post'],
        url_path='shopping_cart',
        permission_classes=[IsAuthenticated],
    )
    def add_to_cart(self, request, pk=None):
        # 1) 404, если нет такого рецепта
        recipe = get_object_or_404(Recipe, pk=pk)
        # 2) попытаемся создать связь
        relation, created = ShoppingList.objects.get_or_create(
            user=request.user,
            recipe=recipe
        )
        if not created:
            return Response(
                {'detail': 'Рецепт уже в корзине'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = RecipeMinifiedSerializer(
            recipe,
            context=self.get_serializer_context()
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @add_to_cart.mapping.delete
    def remove_from_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted, _ = ShoppingList.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted:
            return Response(
                {'detail': 'Рецепт не был в корзине'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        url_path='download_shopping_cart',
        permission_classes=[IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        user = request.user
        qs = RecipeIngredient.objects.filter(
            recipe__shopping_recipe__user=user
        ).values(
            name=F('ingredient__name'),
            unit=F('ingredient__measurement_unit')
        ).annotate(total=Sum('amount'))

        lines = []
        for item in qs:
            lines.append(f"{item['name']} — {item['total']} {item['unit']}")
        content = '\n'.join(lines)

        response = HttpResponse(
            content, content_type='text/plain; charset=utf-8'
        )
        response[
            'Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return response

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        relative = f'/api/s/{recipe.short_url}/'
        full_url = request.build_absolute_uri(relative)
        return Response({'short-link': full_url}, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
        url_name='favorite',
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            _, created = Favourites.objects.get_or_create(
                user=request.user, recipe=recipe
            )
            if not created:
                return Response(
                    {'detail': 'Рецепт уже в избранном'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            serializer = RecipeMinifiedSerializer(
                recipe,
                context=self.get_serializer_context()
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        deleted, _ = Favourites.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted:
            return Response(
                {'detail': 'Рецепт не был в избранном'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = RecipeMinifiedSerializer(
            recipe,
            context=self.get_serializer_context()
        )
        return Response(serializer.data, status=status.HTTP_204_NO_CONTENT)

    def create(self, request, *args, **kwargs):
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)

        recipe = write_serializer.save()
        read_ser = RecipeDetailSerializer(
            recipe,
            context=self.get_serializer_context()
        )

        return Response(read_ser.data, status=status.HTTP_201_CREATED)


class IngredientViewSet(ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    authentication_classes = ()
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None

    def create(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def partial_update(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    def destroy(self, request, *args, **kwargs):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Только чтение: GET /api/tags/ и GET /api/tags/{pk}/
    Любые попытки POST/PATCH/DELETE будут 405 Method Not Allowed
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit')
    amount = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


def shortlink_redirect(request, code):
    recipe = get_object_or_404(Recipe, short_url=code)
    return redirect(f'/recipes/{recipe.id}/')
