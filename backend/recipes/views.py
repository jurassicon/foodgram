from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import HttpResponse, HttpResponseRedirect
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from recipes.models import (
    Favourites,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingList,
    Tag, )
from recipes.pagination import RecipesPagination
from recipes.serializers import (
    RecipeSerializer,
    IngredientSerializer,
    RecipeMinifiedSerializer,
    RecipeWriteSerializer,
    TagSerializer,
)

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
    """

    queryset = Recipe.objects.all().order_by('id')
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    pagination_class = RecipesPagination
    filterset_class = RecipeFilter
    filter_backends = [DjangoFilterBackend]

    relation_model = ShoppingList
    serializer_class = RecipeMinifiedSerializer

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeWriteSerializer
        return RecipeSerializer

    def get_queryset(self):
        return super().get_queryset().with_user_flags(
            self.request.user
        ).order_by('id')

    def _handle_relation(self, request, pk, relation_model, serializer_cls):
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            obj, created = relation_model.objects.get_or_create(
                user=request.user, recipe=recipe
            )
            if not created:
                return Response({'detail': 'Уже добавлено'},
                                status=status.HTTP_400_BAD_REQUEST)
            data = serializer_cls(recipe,
                                  context=self.get_serializer_context()).data
            return Response(data, status=status.HTTP_201_CREATED)

        deleted, _ = relation_model.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted:
            return Response({'detail': 'Не было добавлено'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post', 'delete'], url_path='shopping_cart',
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        return self._handle_relation(
            request, pk,
            relation_model=ShoppingList,
            serializer_cls=RecipeMinifiedSerializer
        )

    @action(detail=True, methods=['post', 'delete'], url_path='favorite',
            permission_classes=[IsAuthenticated])
    def favorite(self, request, pk=None):
        return self._handle_relation(
            request, pk,
            relation_model=Favourites,
            serializer_cls=RecipeMinifiedSerializer
        )

    @action(detail=False, methods=['get'], url_path='download_shopping_cart',
            permission_classes=[IsAuthenticated])
    def download_shopping_cart(self, request):
        user = request.user
        qs = (
            RecipeIngredient.objects
            .filter(recipe__shoppinglist__user=user)
            .values(
                name=F('ingredient__name'),
                unit=F('ingredient__measurement_unit')
            )
            .annotate(total=Sum('amount'))
            .order_by('name')
        )

        lines = [f"{i['name']} — {i['total']} {i['unit']}" for i in qs]
        content = '\n'.join(lines)
        resp = HttpResponse(content, content_type='text/plain; charset=utf-8')
        resp[
            'Content-Disposition'] = 'attachment; filename="shopping_list.txt"'
        return resp

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        rel = f'/s/{recipe.short_url}/'
        full = request.build_absolute_uri(rel)
        return Response({'short-link': full})


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


def shortlink_redirect(request, code):
    try:
        recipe = Recipe.objects.get(short_url=code)
    except Recipe.DoesNotExist:
        return HttpResponseRedirect('/not-found')
    return HttpResponseRedirect(f'/recipes/{recipe.id}')
