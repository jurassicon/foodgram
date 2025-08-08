from django.urls import include, path
from rest_framework.routers import DefaultRouter

from recipes.views import (
    IngredientViewSet,
    RecipeViewSet,
    TagViewSet,
)
from users.views import UsersViewSet

app_name = 'api'

router = DefaultRouter()
router.register('ingredients', IngredientViewSet, basename='ingredients')
router.register('tags', TagViewSet, basename='tags')
router.register('recipes', RecipeViewSet, basename='recipes')
router.register('users', UsersViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
