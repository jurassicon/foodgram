from django.urls import include, path

urlpatterns = [
    path('', include('users.urls')),
    path('', include('recipes.urls')),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),
]
