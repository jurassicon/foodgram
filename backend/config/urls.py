from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from recipes.views import shortlink_redirect
from users.views import UsersViewSet

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('djoser.urls')),
    path('users/subscriptions/',
         UsersViewSet.as_view({'get': 'subscriptions'}),
         name='user-subscriptions'),
    path('api/', include('api.urls')),
    path('s/<str:code>/', shortlink_redirect, name='short-link'),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
