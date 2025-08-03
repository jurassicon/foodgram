from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import redirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from recipes.models import (Favourites, Ingredient, Recipe, RecipeIngredient,
                            ShoppingList, Tag)
from recipes.pagination import CustomUserPagination
from recipes.serializers import (BaseRecipeSerializer, IngredientSerializer,
                                 RecipeMinifiedSerializer,
                                 RecipeWriteSerializer, TagSerializer)

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

    queryset = Recipe.objects.all().order_by('id')
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    pagination_class = CustomUserPagination
    filterset_class = RecipeFilter
    filter_backends = [DjangoFilterBackend]

    relation_model = ShoppingList
    serializer_class = RecipeMinifiedSerializer

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeWriteSerializer
        return BaseRecipeSerializer

    def create(self, request, *args, **kwargs):
        write_ser = self.get_serializer(data=request.data)
        write_ser.is_valid(raise_exception=True)
        recipe = write_ser.save()
        read_ser = BaseRecipeSerializer(
            recipe, context=self.get_serializer_context()
        )
        return Response(read_ser.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        write_ser = self.get_serializer(
            instance, data=request.data, partial=partial
        )
        write_ser.is_valid(raise_exception=True)
        recipe = write_ser.save()
        read_ser = BaseRecipeSerializer(
            recipe, context=self.get_serializer_context()
        )
        return Response(read_ser.data)

    @action(detail=True, methods=['post', 'delete'], url_path='shopping_cart',
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        if request.method == 'POST':
            return self._add_relation(request, pk)
        return self._remove_relation(request, pk)

    @action(detail=True, methods=['post', 'delete'], url_path='favorite',
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        # временно меняем миксин на Favourites
        orig_model, orig_ser = self.relation_model, self.serializer_class
        self.relation_model, self.serializer_class = (Favourites,
                                                      RecipeMinifiedSerializer)
        resp = self._add_relation(request, pk) if request.method == 'POST' \
            else self._remove_relation(request, pk)
        self.relation_model, self.serializer_class = orig_model, orig_ser
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


class IngredientViewSet(ReadOnlyModelViewSet):
    """
    Manages the interaction with the Ingredient resources.

    This class provides a viewset for interacting with the Ingredient model. It
    implements basic filtering and permissions, and it disables specific HTTP
    methods (create, update, partial_update, and destroy). This ensures that
    the Ingredient resources are immutable from client interactions through
    these methods.
    """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    authentication_classes = ()
    permission_classes = (AllowAny,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None


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
