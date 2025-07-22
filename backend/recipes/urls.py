# recipes/urls.py
from rest_framework.routers import DefaultRouter
from recipes.views import RecipeViewSet, TagViewSet, IngredientViewSet

router = DefaultRouter()
router.register('recipes',    RecipeViewSet,     basename='recipes')
router.register('tags',       TagViewSet,        basename='tags')
router.register('ingredients', IngredientViewSet, basename='ingredients')

urlpatterns = router.urls
