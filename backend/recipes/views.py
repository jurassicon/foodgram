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
        recipe = get_object_or_404(Recipe, pk=pk)
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
        """
        DELETE /api/recipes/{pk}/shopping_cart/
        """
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted, _ = ShoppingList.objects.filter(
            user=request.user,
            recipe=recipe
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

    def __create_obj_recipes(self, serializer, request, pk):
        data = {'user': request.user.id, 'recipe': int(pk)}
        serializer_obj = serializer(
            data=data, context=self.get_serializer_context()
        )
        serializer_obj.is_valid(raise_exception=True)
        serializer_obj.save()
        return Response(serializer_obj.data, status=status.HTTP_201_CREATED)

    def __update_obj_recipes(self, serializer, request, pk):
        data = {'user': request.user.id, 'recipe': int(pk)}
        serializer_obj = serializer(
            data=data, context=self.get_serializer_context()
        )
        serializer_obj.is_valid(raise_exception=True)
        serializer_obj.save()
        return Response(serializer_obj.data, status=status.HTTP_200_OK)

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
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            relation, created = Favourites.objects.get_or_create(
                user=request.user,
                recipe=recipe
            )
            if not created:
                return Response(
                    {'detail': 'Ошибка добавления в избранное'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = RecipeMinifiedSerializer(
                recipe,
                context=self.get_serializer_context()
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        deleted, _ = Favourites.objects.filter(
            user=request.user,
            recipe=recipe
        ).delete()
        if not deleted:
            return Response(
                {'detail': 'Рецепта не было в избранном'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

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
