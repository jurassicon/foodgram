from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import AllowAny
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from recipes.pagination import CustomPagination
from recipes.models import Ingredient, Recipe, Tag
from recipes.serializers import IngredientSerializer, RecipeSerializer, \
    TagSerializer


class RecipeViewSet(viewsets.ModelViewSet):

    queryset = Recipe.objects.all().order_by('id')  # или любое другое поле
    serializer_class = RecipeSerializer
    pagination_class = CustomPagination

    filter_backends = [DjangoFilterBackend]
    permission_classes = [AllowAny]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticatedOrReadOnly
        return [IsAuthenticatedOrReadOnly()]


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]

    filter_backends = [filters.SearchFilter]
    filterset_fields = ('name',)
    search_fields = ('name',)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None
