# project/urls.py
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from recipes.views import RecipeViewSet, TagViewSet

router = DefaultRouter()
router.register('recipes', RecipeViewSet, basename='recipes')
router.register('tags', TagViewSet, basename='tags')

urlpatterns = [
    path('admin/', admin.site.urls),
    #path('api/users/', include('users.urls')),  # ← теперь ровно под /api/users/
    #path('api/', include(router.urls)),         # /api/recipes/, /api/tags/ и т.д.
    path('api/', include('users.urls')),
]