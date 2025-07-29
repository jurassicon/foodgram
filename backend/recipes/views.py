from django.contrib.auth import get_user_model
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
    FavouritesSerializer, ShoppingListSerializer, \
    RecipeDetailSerializer, RecipeListSerializer

User = get_user_model()


class RecipeViewSet(viewsets.ModelViewSet):
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

    @action(
        detail=True,
        methods=['post'],
        url_path='shopping_cart',
        permission_classes=[IsAuthenticated],
    )
    def add_to_cart(self, request, pk=None):
        recipe = get_object_or_404(Recipe, pk=pk)
        serializer = ShoppingListSerializer(
            data={'user': request.user.id, 'recipe': pk},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @add_to_cart.mapping.delete
    def remove_from_cart(self, request, pk=None):
        """
        DELETE /api/recipes/{pk}/shopping_cart/
        """
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted, _ = ShoppingList.objects.filter(
            user=request.user,
            recipe=recipe
        ).delete()
        if not deleted:
            # если этой записи не было в корзине — 400
            return Response(
                {'detail': 'Рецепт не был в корзине'},
                status=status.HTTP_400_BAD_REQUEST
            )
        # корректное удаление — 204 No Content
        return Response(status=status.HTTP_204_NO_CONTENT)

    def __create_obj_recipes(self, serializer, request, pk):
        data = {'user': request.user.id, 'recipe': int(pk)}
        serializer_obj = serializer(
            data=data, context=self.get_serializer_context()
        )
        serializer_obj.is_valid(raise_exception=True)
        serializer_obj.save()
        return Response(serializer_obj.data, status=status.HTTP_201_CREATED)

    def __delete_obj_recipes(self, request, model, pk):
        delete_count, _ = model.objects.filter(
            user=request.user, recipe__id=pk
        ).delete()
        if delete_count == 0:
            return Response({'errors': 'Рецепт уже удален'},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=('POST', 'DELETE'),
            detail=True,
            permission_classes=(IsAuthenticated,),
            url_path='favorite',
            url_name='favorite')
    def favorite(self, request, pk=None):
        get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            return self.__create_obj_recipes(
                FavouritesSerializer, request, pk
            )
        return self.__delete_obj_recipes(request, Favourites, pk)

    def create(self, request, *args, **kwargs):
        # 1. Валидация входных данных через write-сериализатор
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)

        # 2. Сохраняем новый рецепт и связанные объекты
        recipe = write_serializer.save()
        read_ser = RecipeDetailSerializer(
            recipe,
            context=self.get_serializer_context()
        )
        # 3. Готовим ответ через RecipeListSerializer
        #list_serializer = RecipeListSerializer(
        #    recipe,
        #    context=self.get_serializer_context()
        #)

        return Response(read_ser.data, status=status.HTTP_201_CREATED)


class IngredientViewSet(ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    authentication_classes = ()        # отключаем аутентификацию
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
