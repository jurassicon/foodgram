# users/urls.py
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from users.views import UserViewSet, SignUpViewSet

app_name = 'users'

router = DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('auth/signup', SignUpViewSet, basename='signup')

urlpatterns = router.urls

urlpatterns = [
    # базовые user-эндпоинты:
    #   GET  /api/users/      — список (требует токен)
    #   POST /api/users/      — регистрация (AllowAny)
    #   GET  /api/users/me/   — профиль (требует токен)
    #   PATCH/DELETE /api/users/{id}/  — редактирование/удаление
    path('', include('djoser.urls')),

    # токенная авторизация:
    #   POST /api/users/token/login/   — получить токен по email+pass (AllowAny)
    #   POST /api/users/token/logout/  — удалить токен (требует токен)
    path('', include('djoser.urls.authtoken')),
]
