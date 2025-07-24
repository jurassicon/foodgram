from djoser.views import UserViewSet
from rest_framework import (
    viewsets, permissions, status)
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import User
from .serializers import UserRegistrationSerializer, UserSerializer, \
    AvatarSerializer


class CustomUserViewSet(UserViewSet):
    pagination_class = None
    serializer_class = UserSerializer
    queryset = User.objects.all()

    @action(
        detail=False,
        methods=['put', 'DELETE', ],
        url_path='me/avatar',
        permission_classes=[IsAuthenticated, ],
        parser_classes=[MultiPartParser],
    )
    def avatar(self, request):
        """
        GET  /api/users/me/avatar/ — вернуть URL текущего аватара
        PUT  /api/users/me/avatar/ — загрузить новый аватар
        """
        if request.method == 'PUT':
            serializer = AvatarSerializer(
                self.request.user,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        # GET
        self.request.user.avatar = None
        self.request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        url_path='me',
        methods=['GET', 'PATCH'],
        permission_classes=[permissions.IsAuthenticated, ],
    )
    def me_url(self, request):
        user = request.user
        if request.method == 'PATCH':
            serializer = self.get_serializer(user, data=request.data,
                                             partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(user, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SignUpViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
