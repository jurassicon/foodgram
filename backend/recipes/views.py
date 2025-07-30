from django.contrib.auth import get_user_model
from django.db.models import Sum, F, Model
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


class AddRemoveMixin:
    """
    Mixin class providing utility methods for managing relationships between
    users and predefined recipes. This class is intended to simplify adding
    and removing relationships such as favorites or likes using methods that
    operate on relational models.

    It assumes the presence of a specified relational model `relation_model`
    and serializer class to handle related operations consistently.
    These attributes must be defined in subclasses for the mixin to
    function correctly.
    """

    relation_model = None
    serializer_class = None

    def _add_relation(self, request, pk):
        recipe = get_object_or_404(self.queryset.model, pk=pk)
        _, created = self.relation_model.objects.get_or_create(
            user=request.user, recipe=recipe
        )
        if not created:
            return Response(
                {'detail': 'Уже добавлено'},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = self.serializer_class(
            recipe, context=self.get_serializer_context()
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _remove_relation(self, request, pk):
        recipe = get_object_or_404(self.queryset.model, pk=pk)
        deleted, _ = self.relation_model.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted:
            return Response(
                {'detail': 'Не было добавлено'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class RecipeViewSet(AddRemoveMixin, viewsets.ModelViewSet):
    """
    A view set for managing recipes in the system.

    This view set provides functionality for creating, retrieving, updating,
    and deleting recipes, as well as custom actions such as adding/removing
    recipes from a shopping cart, downloading a shopping list, retrieving
    a short link for a recipe, and managing favorite recipes. It supports
    different serializers depending on the action, allows fine-grained
    permission control, and integrates with custom filtering, pagination,
    and backend configurations.
    """

    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    queryset = Recipe.objects.all().order_by('id')
    pagination_class = CustomUserPagination
    filterset_class = RecipeFilter
    filter_backends = [DjangoFilterBackend]
    relation_model = ShoppingList
    serializer_class = RecipeMinifiedSerializer

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeWriteSerializer
        if self.action == 'list':
            return RecipeListSerializer
        return RecipeDetailSerializer


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
        methods=['post', 'delete'],
        url_path='shopping_cart',
        permission_classes=[IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        if request.method == 'POST':
            return self._add_relation(request, pk)
        return self._remove_relation(request, pk)

    # Переопределяем атрибуты миксина для избранного
    @property
    def _favorite_relation_model(self):
        return Favourites

    @property
    def _favorite_serializer_class(self):
        return RecipeMinifiedSerializer

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='favorite',
        permission_classes=[IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        # временно подменяем relation_model и serializer_class
        orig_model = self.relation_model
        orig_serializer = self.serializer_class
        self.relation_model = self._favorite_relation_model
        self.serializer_class = self._favorite_serializer_class

        if request.method == 'POST':
            resp = self._add_relation(request, pk)
        else:
            resp = self._remove_relation(request, pk)

        # восстанавливаем
        self.relation_model = orig_model
        self.serializer_class = orig_serializer
        return resp

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
