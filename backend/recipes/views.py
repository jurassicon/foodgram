from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated, \
    IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from api.filters import RecipeFilter, IngredientFilter
from api.permissions import IsAuthorOrReadOnly
from recipes.models import Ingredient, Recipe, Tag, RecipeIngredient, \
    ShoppingList, Favourites
from recipes.pagination import CustomPagination
from recipes.serializers import IngredientSerializer, \
    TagSerializer, RecipeWriteSerializer, \
    FavouritesSerializer, ShoppingListSerializer, \
    RecipeDetailSerializer

User = get_user_model()


class RecipeViewSet(viewsets.ModelViewSet):
    permission_classes = (IsAuthorOrReadOnly,)
    queryset = Recipe.objects.all().order_by('id')  # или любое другое поле
    pagination_class = CustomPagination
    filterset_class = RecipeFilter
    filter_backends = [DjangoFilterBackend]

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return RecipeWriteSerializer
        # и на list, и на retrieve — деталка
        return RecipeDetailSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_permissions(self):
        from rest_framework.permissions import IsAuthenticatedOrReadOnly
        return [IsAuthenticatedOrReadOnly()]

    @action(methods=('POST', 'DELETE',),
            detail=True,
            permission_classes=(IsAuthenticated,),
            url_name='shopping_cart',
            url_path='shopping_cart')
    def add_shopping_item(self, request, pk=None):
        get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            return self.__create_obj_recipes(
                ShoppingListSerializer, request, pk
            )
        return self.__delete_obj_recipes(request, ShoppingList, pk)

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
        # 1) валидируем и сохраняем через write-сериализатор
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        recipe = write_serializer.save()  # здесь HiddenField CurrentUserDefault уже подставил author

        # 2) «пересериализуем» только что созданный объект через detail-сериализатор
        read_serializer = RecipeDetailSerializer(
            recipe,
            context=self.get_serializer_context()
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)  # теперь GET разрешён всем
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagViewSet(viewsets.ModelViewSet):
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


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(source='profile.avatar', read_only=True)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name',
            'is_subscribed', 'avatar',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or request.user.is_anonymous:
            return False
        return obj.followers.filter(user=request.user).exists()
