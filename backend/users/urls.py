# users/urls.py
from django.urls import include, path

app_name = 'users'

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
