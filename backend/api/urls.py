from django.urls import include, path
from rest_framework.routers import DefaultRouter

from users.views import (
    UserViewSet, SignUpViewSet, ConfirmationCodeTokenView
)

router_v1 = DefaultRouter()

router_v1.register('users', UserViewSet, basename='users')
router_v1.register('auth/signup', SignUpViewSet, basename='signup')

urlpatterns = [
    path('v1/', include(router_v1.urls)),
    path(
        'v1/auth/token/',
        ConfirmationCodeTokenView.as_view(),
        name='confirmation_code_token'
    ),
]
